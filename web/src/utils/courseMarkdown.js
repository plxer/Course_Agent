import { Marked } from 'marked'

const URL_SCHEME = /^(https?:\/\/|www\.)/i
const HOST_CHAR = /[A-Za-z0-9\-._:@]/
const PATH_CHAR = /[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]/
const TRAILING_PUNCT = /[.,;:!?、。，；：？！…·"'`]+$/
const CJK_LETTER =
  /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]/
const PLACEHOLDER = (i) => `@@URL${i}@@`

const courseMarked = new Marked()
courseMarked.use({
  gfm: true,
  breaks: true,
  tokenizer: {
    // 关掉 GFM 自动识别：www.xxx 后面没有空格时会把整句中文吃进链接
    url() {
      return undefined
    },
  },
})

function isCjkLetter(ch) {
  return CJK_LETTER.test(ch)
}

function isUrlStop(ch) {
  if (!ch) return true
  const c = ch.codePointAt(0)
  if (c <= 32) return true
  if (c >= 0x2000 && c <= 0x206f) return true
  if (c >= 0x3000 && c <= 0x303f) return true
  if (c >= 0xff00 && c <= 0xffef) return true
  return '<>"\'`（）【】「」『』《》〈〉'.includes(ch)
}

function decodeHref(href) {
  let out = (href || '').replace(/&amp;/g, '&')
  try {
    out = decodeURI(out)
  } catch {
    /* keep */
  }
  return out
}

function toHref(url) {
  if (!url) return ''
  if (/^www\./i.test(url)) return `https://${url}`
  if (/^https?:\/\//i.test(url)) return url
  return ''
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function trimUrl(url) {
  let s = url
  while (s.length && TRAILING_PUNCT.test(s)) s = s.replace(TRAILING_PUNCT, '')
  while (s.endsWith(')') && (s.match(/\(/g) || []).length < (s.match(/\)/g) || []).length) {
    s = s.slice(0, -1)
  }
  while (s.endsWith(']') && (s.match(/\[/g) || []).length < (s.match(/]/g) || []).length) {
    s = s.slice(0, -1)
  }
  return s
}

/** 切出一段网址；遇到中文、全角括号立刻停，避免把后面正文划进链接 */
export function takeUrlAt(text, start) {
  const prefix = text.slice(start).match(URL_SCHEME)
  if (!prefix) return null
  if (start > 0 && /[A-Za-z0-9/_-]/i.test(text[start - 1] || '')) return null

  let i = start + prefix[0].length
  let pathStarted = false
  while (i < text.length) {
    const ch = text[i]
    if (isUrlStop(ch)) break
    if (!pathStarted) {
      if (ch === '/' || ch === '?' || ch === '#') {
        pathStarted = true
        i += 1
        continue
      }
      if (HOST_CHAR.test(ch)) {
        i += 1
        continue
      }
      break
    }
    if (PATH_CHAR.test(ch)) {
      i += 1
      continue
    }
    const prev = text[i - 1]
    if (isCjkLetter(ch) && (prev === '/' || isCjkLetter(prev) || prev === '-' || prev === '_')) {
      i += 1
      continue
    }
    break
  }
  const raw = text.slice(start, i)
  const url = trimUrl(raw)
  if (url.length <= prefix[0].length) return null
  return { url, length: url.length }
}

function skipFencedCode(text, i) {
  if (!text.startsWith('```', i)) return -1
  const end = text.indexOf('```', i + 3)
  return end < 0 ? text.length : end + 3
}

function skipInlineCode(text, i) {
  if (text[i] !== '`') return -1
  const end = text.indexOf('`', i + 1)
  return end < 0 ? text.length : end + 1
}

function skipAngleAutolink(text, i) {
  if (!text.startsWith('<http', i) && !text.startsWith('<www.', i)) return -1
  const gt = text.indexOf('>', i + 1)
  return gt < 0 ? -1 : gt + 1
}

function skipMdLink(text, i) {
  const bang = text[i] === '!' && text[i + 1] === '['
  if (!bang && text[i] !== '[') return -1
  const open = bang ? i + 1 : i
  const close = text.indexOf('](', open + 1)
  if (close < 0) return -1
  let j = close + 2
  let depth = 1
  while (j < text.length && depth > 0) {
    const ch = text[j]
    if (ch === '(') depth += 1
    else if (ch === ')') depth -= 1
    j += 1
  }
  return depth === 0 ? j : -1
}

function protectBareUrls(text) {
  const urls = []
  let out = ''
  let i = 0
  while (i < text.length) {
    const fence = skipFencedCode(text, i)
    if (fence >= 0) {
      out += text.slice(i, fence)
      i = fence
      continue
    }
    const code = skipInlineCode(text, i)
    if (code >= 0) {
      out += text.slice(i, code)
      i = code
      continue
    }
    const angle = skipAngleAutolink(text, i)
    if (angle >= 0) {
      out += text.slice(i, angle)
      i = angle
      continue
    }
    const md = skipMdLink(text, i)
    if (md >= 0) {
      out += text.slice(i, md)
      i = md
      continue
    }
    const taken = takeUrlAt(text, i)
    if (taken) {
      out += PLACEHOLDER(urls.length)
      urls.push(taken.url)
      i += taken.length
      continue
    }
    out += text[i]
    i += 1
  }
  return { text: out, urls }
}

function renderUrlAnchor(url) {
  const href = toHref(url)
  if (!href) return escapeHtml(url)
  return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(url)}</a>`
}

function restoreUrlPlaceholders(html, urls) {
  return html.replace(/@@URL(\d+)@@/g, (_, n) => {
    const url = urls[Number(n)]
    return url ? renderUrlAnchor(url) : _
  })
}

function splitGreedyAnchors(html) {
  return html.replace(/<a\s+([^>]*?)>([\s\S]*?)<\/a>/gi, (full, attrs, inner) => {
    if (/page-link/.test(attrs) || /data-book-id=/.test(attrs)) return full
    const innerText = inner.replace(/<[^>]+>/g, '')
    if (innerText && URL_SCHEME.test(innerText)) {
      const innerTaken = takeUrlAt(innerText, 0)
      if (
        innerTaken &&
        innerTaken.length < innerText.length &&
        innerTaken.url === innerText.slice(0, innerTaken.length)
      ) {
        return `${renderUrlAnchor(innerTaken.url)}${escapeHtml(innerText.slice(innerTaken.length))}`
      }
      if (innerTaken) {
        let nextAttrs = attrs.replace(/\bhref="[^"]*"/i, `href="${escapeHtml(toHref(innerTaken.url))}"`)
        if (!/\btarget=/i.test(nextAttrs)) nextAttrs += ' target="_blank" rel="noopener noreferrer"'
        return `<a ${nextAttrs}>${escapeHtml(innerTaken.url)}</a>`
      }
    }
    const hrefMatch = attrs.match(/\bhref="([^"]*)"/i)
    if (!hrefMatch) return full
    const decoded = decodeHref(hrefMatch[1])
    const taken = takeUrlAt(decoded, 0)
    const cleanHref = taken ? toHref(taken.url) : toHref(trimUrl(decoded))
    if (!cleanHref) return full
    let nextAttrs = attrs.replace(/\bhref="[^"]*"/i, `href="${escapeHtml(cleanHref)}"`)
    if (!/\btarget=/i.test(nextAttrs)) nextAttrs += ' target="_blank" rel="noopener noreferrer"'
    return `<a ${nextAttrs}>${inner}</a>`
  })
}

export function renderCourseMarkdown(text) {
  if (!text || typeof text !== 'string') return ''
  const { text: protectedText, urls } = protectBareUrls(text)
  const html = courseMarked.parse(protectedText)
  return splitGreedyAnchors(restoreUrlPlaceholders(html, urls))
}

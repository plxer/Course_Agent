"""课本《计算机网络：自顶向下方法》章节目录与片段读取，用于出题时结合课本内容。"""

import re
from pathlib import Path

# 课本路径（与 knowledgebase 中一致）
TEXTBOOK_PATH = Path(__file__).resolve().parents[2] / "knowledgebase" / "ComputerNetworking-TopDown" / "ComputerNetworking-TopDown.md"

# 章标题（与课本目录对应）
CHAPTER_TITLES = {
    1: "第1章 计算机网络和因特网",
    2: "第2章 应用层",
    3: "第3章 传输层",
    4: "第4章 网络层：数据平面",
    5: "第5章 网络层：控制平面",
    6: "第6章 链路层和局域网",
    7: "第7章 无线网络与移动网络",
    8: "第8章 计算机网络安全",
}

# 每章的具体重要知识点（非小节名称，用于出题时选择）。section_id 用于截取课本片段。
# 结构: chapter_id -> [ {"id": "xxx", "title": "知识点名称", "section_id": "1.1"}, ... ]
CHAPTER_KNOWLEDGE_POINTS: dict[int, list[dict]] = {
    1: [
        {"id": "internet_basics", "title": "因特网的定义与组成（主机、链路、分组、路由器、ISP、TCP/IP）", "section_id": "1.1"},
        {"id": "protocol_standards", "title": "协议与标准（协议的概念、IETF、RFC）", "section_id": "1.1.3"},
        {"id": "network_edge_access", "title": "网络边缘与接入网（DSL、电缆、FTTH、以太网、WiFi）", "section_id": "1.2"},
        {"id": "physical_media", "title": "物理媒体（双绞线、同轴电缆、光纤、无线电）", "section_id": "1.2.2"},
        {"id": "packet_circuit_switching", "title": "分组交换与电路交换（存储转发、排队时延、FDM/TDM）", "section_id": "1.3"},
        {"id": "network_of_networks", "title": "网络中的网络（ISP 层次、PoP）", "section_id": "1.3.3"},
        {"id": "delay_throughput", "title": "时延与吞吐量（四类时延、端到端时延、吞吐量）", "section_id": "1.4"},
        {"id": "protocol_layers", "title": "协议分层与封装（五层模型、PDU、各层职责）", "section_id": "1.5"},
        {"id": "security_threats", "title": "网络安全威胁（恶意软件、DDoS、嗅探、伪装）", "section_id": "1.6"},
    ],
    2: [
        {"id": "app_architectures", "title": "网络应用架构（C/S、P2P）", "section_id": "2.1.1"},
        {"id": "process_socket", "title": "进程通信与套接字（端口、寻址）", "section_id": "2.1.2"},
        {"id": "transport_services", "title": "运输层服务（可靠传输、吞吐量、定时、安全）", "section_id": "2.1.3"},
        {"id": "tcp_udp_services", "title": "TCP 与 UDP 服务（面向连接/无连接）", "section_id": "2.1.4"},
        {"id": "http_basics", "title": "HTTP（非持久/持久连接、请求与响应格式、Cookie）", "section_id": "2.2"},
        {"id": "web_caching", "title": "Web 缓存与条件 GET", "section_id": "2.2.5"},
        {"id": "smtp_mail", "title": "SMTP 与邮件访问协议（IMAP、HTTP）", "section_id": "2.3"},
        {"id": "dns", "title": "DNS（层次数据库、解析过程、记录与报文）", "section_id": "2.4.1"},
        {"id": "p2p_bittorrent", "title": "P2P 文件分发与 BitTorrent", "section_id": "2.5"},
        {"id": "video_cdn", "title": "视频流与 CDN（DASH、Netflix/YouTube）", "section_id": "2.6.1"},
    ],
    3: [
        {"id": "transport_overview", "title": "传输层概述（与网络层关系、UDP/TCP）", "section_id": "3.1"},
        {"id": "multiplexing", "title": "多路复用与多路分解", "section_id": "3.2"},
        {"id": "udp", "title": "UDP（无连接、报文段结构、校验和）", "section_id": "3.3"},
        {"id": "reliable_transfer", "title": "可靠数据传输原理（RDT、流水线、GBN、SR）", "section_id": "3.4"},
        {"id": "tcp_connection", "title": "TCP 连接（三次握手、四次挥手）", "section_id": "3.5.1"},
        {"id": "tcp_segment", "title": "TCP 报文段结构与 RTT、超时", "section_id": "3.5.2"},
        {"id": "tcp_flow_control", "title": "TCP 流量控制与连接管理", "section_id": "3.5.5"},
        {"id": "congestion_control", "title": "拥塞控制原理与 TCP 拥塞控制（慢启动、拥塞避免）", "section_id": "3.6"},
    ],
    4: [
        {"id": "forwarding_routing", "title": "转发与路由、数据平面与控制平面", "section_id": "4.1"},
        {"id": "router_inside", "title": "路由器内部（输入/输出端口、交换、排队、调度）", "section_id": "4.2"},
        {"id": "ipv4", "title": "IPv4 数据报格式与编址", "section_id": "4.3.1"},
        {"id": "nat", "title": "NAT（网络地址转换）", "section_id": "4.3.3"},
        {"id": "ipv6", "title": "IPv6", "section_id": "4.3.4"},
        {"id": "generalized_forwarding", "title": "通用转发与 SDN（Match-Action）", "section_id": "4.4"},
        {"id": "middleboxes", "title": "中间盒（防火墙、NAT、负载均衡）", "section_id": "4.5"},
    ],
    5: [
        {"id": "routing_algorithms", "title": "路由算法（链路状态 LS、距离向量 DV）", "section_id": "5.2"},
        {"id": "ospf", "title": "域内路由：OSPF", "section_id": "5.3"},
        {"id": "bgp", "title": "域间路由：BGP（路由通告、选路、策略）", "section_id": "5.4"},
        {"id": "sdn_control", "title": "SDN 控制平面与 OpenFlow", "section_id": "5.5"},
        {"id": "icmp", "title": "ICMP（互联网控制报文协议）", "section_id": "5.6"},
        {"id": "snmp_netconf", "title": "网络管理（SNMP、NETCONF/YANG）", "section_id": "5.7.1"},
    ],
    6: [
        {"id": "link_layer_services", "title": "链路层服务与实现位置", "section_id": "6.1"},
        {"id": "error_detection", "title": "差错检测与纠正（奇偶校验、校验和、CRC）", "section_id": "6.2"},
        {"id": "multiple_access", "title": "多路访问协议（信道划分、随机接入、轮转）", "section_id": "6.3"},
        {"id": "arp_ether", "title": "链路层寻址与 ARP、以太网", "section_id": "6.4.1"},
        {"id": "switches_vlan", "title": "链路层交换机与 VLAN", "section_id": "6.4.3"},
        {"id": "mpls", "title": "链路虚拟化与 MPLS", "section_id": "6.5.1"},
        {"id": "data_center", "title": "数据中心网络", "section_id": "6.6.1"},
    ],
    7: [
        {"id": "wireless_intro", "title": "无线链路与网络特性（CDMA、隐藏终端、衰落）", "section_id": "7.2"},
        {"id": "wifi_80211", "title": "WiFi 802.11（体系结构、MAC 协议、帧格式）", "section_id": "7.3.1"},
        {"id": "cellular_4g5g", "title": "蜂窝网络 4G/5G（LTE 架构与协议栈）", "section_id": "7.4.1"},
        {"id": "mobility_management", "title": "移动性管理（归属网络、间接/直接路由、Mobile IP）", "section_id": "7.5"},
    ],
    8: [
        {"id": "security_principles", "title": "网络安全原则与密码学基础", "section_id": "8.2"},
        {"id": "integrity_signatures", "title": "报文完整性、散列、MAC、数字签名", "section_id": "8.3"},
        {"id": "auth", "title": "端点认证", "section_id": "8.4"},
        {"id": "secure_email", "title": "安全电子邮件（PGP）", "section_id": "8.5.1"},
        {"id": "tls", "title": "TCP 安全：TLS/SSL", "section_id": "8.6.1"},
        {"id": "ipsec_vpn", "title": "网络层安全：IPsec 与 VPN", "section_id": "8.7.1"},
        {"id": "wifi_cellular_security", "title": "无线 LAN 与蜂窝网安全", "section_id": "8.8.1"},
        {"id": "firewall_ids", "title": "防火墙与入侵检测", "section_id": "8.9.1"},
    ],
}

# 节标题正则：匹配 # 1.1 **Title**、# **2.4** Title、# 7.3 WiFi 等
SECTION_HEADER = re.compile(r"^#\s*\*{0,2}\s*(\d+\.\d+(?:\.\d+)?)\s*\*{0,2}\s*(.*)$")


def _scan_sections() -> list[tuple[str, int, str]]:
    """扫描课本文件，返回 (section_id, line_1based, title) 列表，按行号排序。"""
    if not TEXTBOOK_PATH.exists():
        return []
    result = []
    with open(TEXTBOOK_PATH, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            m = SECTION_HEADER.match(line)
            if m:
                sec_id = m.group(1)
                ch_num = int(sec_id.split(".")[0])
                if ch_num < 1 or ch_num > 8:
                    continue  # 仅保留第1–8章
                title = m.group(2).strip().strip("*").strip()
                result.append((sec_id, i, title))
    return result


def get_textbook_chapters() -> list[dict]:
    """
    返回课本章节目录，用于前端先选章节、再选知识点。
    知识点为每章的具体重要概念（非小节名称）。
    结构：[ { "id": 1, "title": "第1章 ...", "knowledge_points": [ { "id", "title", "section_id" }, ... ] }, ... ]
    """
    chapters: list[dict] = []
    for ch_num in sorted(CHAPTER_TITLES.keys()):
        points = CHAPTER_KNOWLEDGE_POINTS.get(ch_num, [])
        chapters.append({
            "id": ch_num,
            "title": CHAPTER_TITLES[ch_num],
            "knowledge_points": [{"id": p["id"], "title": p["title"], "section_id": p["section_id"]} for p in points],
        })
    return chapters


def get_section_title(section_id: str | None) -> str:
    """
    根据小节 ID 返回课本中该小节的标题（如 1.1 -> "What Is the Internet?"），
    用于在界面上展示本题结合了课本的哪一部分。
    """
    if not section_id or not TEXTBOOK_PATH.exists():
        return ""
    for sec_id, _line, title in _scan_sections():
        if sec_id == section_id:
            return title.strip()
    return ""


def get_textbook_excerpt(chapter: int | str, section_id: str | None = None, max_chars: int = 12000) -> str:
    """
    根据章节与可选的小节 ID 截取课本片段，用于出题时作为上下文。
    chapter: 章号 1-8 或 "1"
    section_id: 如 "1.1"、"2.4.1"，若为 None 则截取整章（可能较长，会截断）
    max_chars: 最大字符数，避免超出模型上下文。
    """
    ch_num = int(chapter) if isinstance(chapter, str) else chapter
    if not TEXTBOOK_PATH.exists():
        return ""

    sections = _scan_sections()
    # 确定起止行：若指定 section_id 则只取该节，否则取整章
    start_line = None
    end_line = None

    for i, (sec_id, line_no, _) in enumerate(sections):
        if int(sec_id.split(".")[0]) != ch_num:
            if start_line is not None:
                end_line = line_no
                break
            continue
        if section_id is None and start_line is None:
            start_line = line_no
        elif section_id and sec_id == section_id:
            start_line = line_no
            if i + 1 < len(sections) and int(sections[i + 1][0].split(".")[0]) == ch_num:
                end_line = sections[i + 1][1]
            break
        elif section_id is None:
            pass  # 继续找下一章的开头作为 end_line

    if start_line is None:
        return ""

    if end_line is None:
        # 整章到文件末尾或下一章
        for sec_id, line_no, _ in sections:
            if int(sec_id.split(".")[0]) > ch_num:
                end_line = line_no
                break
        if end_line is None:
            end_line = 999999

    lines = []
    with open(TEXTBOOK_PATH, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()
    for j in range(start_line - 1, min(end_line - 1, len(all_lines))):
        lines.append(all_lines[j])
    text = "".join(lines).strip()
    if len(text) > max_chars:
        text = text[: max_chars] + "\n\n…（内容已截断）"
    return text

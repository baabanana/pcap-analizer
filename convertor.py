from scapy.utils import rdpcap
from scapy.packet import Packet
import csv
import logging
import json
import math

def load_pcap(file_path):
    """
    加载PCAP文件并返回数据包列表
    """
    packets = rdpcap(file_path)
    logging.info(f"Loaded {len(packets)} packets from {file_path}")
    return packets


def split_pcap_to_csv(packets, session_id):
    """
    简化版：只保存源、目标、协议、摘要
    """
    
    headers = ['No.', 'Source', 'Destination', 'Protocol', 'Info']
    rows = []
    
    for idx, pkt in enumerate(packets, start=1):
        # 提取源地址
        src = ''
        if pkt.haslayer('IP'):
            src = pkt['IP'].src
        elif pkt.haslayer('IPv6'):
            src = pkt['IPv6'].src
        elif pkt.haslayer('Ether'):
            src = pkt['Ether'].src
        
        # 提取目标地址
        dst = ''
        if pkt.haslayer('IP'):
            dst = pkt['IP'].dst
        elif pkt.haslayer('IPv6'):
            dst = pkt['IPv6'].dst
        elif pkt.haslayer('Ether'):
            dst = pkt['Ether'].dst
        
        # 提取协议
        protocol = ''
        if pkt.haslayer('TCP'):
            protocol = 'TCP'
        elif pkt.haslayer('UDP'):
            protocol = 'UDP'
        elif pkt.haslayer('ICMP'):
            protocol = 'ICMP'
        elif pkt.haslayer('ICMPv6'):
            protocol = 'ICMPv6'
        elif pkt.haslayer('ARP'):
            protocol = 'ARP'
        elif pkt.haslayer('DNS'):
            protocol = 'DNS'
        else:
            protocol = pkt.summary().split()[0]
        
        rows.append({
            'No.': idx,
            'Source': src,
            'Destination': dst,
            'Protocol': protocol,
            'Info': pkt.summary()
        })
    
    # 确保data目录存在
    import os
    os.makedirs('data', exist_ok=True)

    # 写入CSV
    output_csv = f"data/{session_id}_summary.csv"

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    logging.info(f"✅ 导出完成：{len(rows)} 个数据包 -> {output_csv}")
    return output_csv

def packet_to_dict(pkt):
    """递归提取数据包的所有层和字段"""
    packet_dict = {
        'summary': pkt.summary(),
        'timestamp': float(pkt.time) if hasattr(pkt, 'time') else None,
        'length': len(pkt),
        'layers': []
    }
    
    # 遍历所有协议层
    layer = pkt
    while layer:
        layer_dict = {
            'layer_name': layer.name,
            'fields': {}
        }
        
        # 提取该层的所有字段
        for field_name, field_value in layer.fields.items():
            # 处理不同类型的字段值
            if isinstance(field_value, bytes):
                layer_dict['fields'][field_name] = field_value.hex()
            elif isinstance(field_value, Packet):
                # 如果字段值是另一个数据包，递归处理
                layer_dict['fields'][field_name] = packet_to_dict(field_value)
            else:
                layer_dict['fields'][field_name] = str(field_value)
        
        packet_dict['layers'].append(layer_dict)
        layer = layer.payload if layer.payload else None
    
    return packet_dict

def split_pcap_to_json(packets, session_id, num_files=10):
    # 读取数据包
    total_packets = len(packets)

    # 计算每个文件应包含的数据包数量
    packets_per_file = math.ceil(total_packets / num_files)

    print(f"总共 {total_packets} 个数据包，将拆分为 {num_files} 个文件")
    print(f"每个文件约 {packets_per_file} 个数据包")

    filename_list=[]
    # 拆分并保存
    for file_index in range(num_files):
        start_idx = file_index * packets_per_file
        end_idx = min(start_idx + packets_per_file, total_packets)
        
        # 如果起始索引已经超出范围，跳出循环
        if start_idx >= total_packets:
            break
        
        packets_json = []
        for i in range(start_idx, end_idx):
            packet_data = packet_to_dict(packets[i])
            packet_data['packet_index'] = i  # 保持原始索引
            packets_json.append(packet_data)
        
        # 确保data目录存在
        import os
        os.makedirs('data', exist_ok=True)

        # 保存为单独的 JSON 文件
        filename = f'data/{session_id}_packets_part_{file_index + 1:02d}.json'
        filename_list.append(filename)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(packets_json, f, indent=2, ensure_ascii=False)
        
        print(f"✓ {filename}: 包含数据包 {start_idx}-{end_idx-1} ({len(packets_json)} 个)")

    return filename_list


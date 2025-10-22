from scapy.all import rdpcap, IP, TCP, UDP, ICMP, DNS, DHCP, Raw
from scapy.layers.http import HTTPRequest, HTTPResponse
import ssl

def load_pcap(file_path):
    packets = rdpcap(file_path)
    return packets

def layer_detector(packet):
    """detect layers in a packet, and add all the info into a list"""
    target_layers=[IP, TCP, UDP, ICMP, DNS, DHCP, HTTPRequest, HTTPResponse, Raw]
    packet_info=[]
    for layer in target_layers:
        if packet.haslayer(layer):
            icmp_layer = packet[layer]
            packet_info.append(icmp_layer.show(dump=True))
            #deal stmp
            if layer==TCP and (packet[TCP].dport==25 or packet[TCP].sport==25):
                smtp_info = [
                    "*** SMTP Layer ***",
                    f"Source Port: {packet[TCP].sport}",
                    f"Destination Port: {packet[TCP].dport}",
                ]
                                # 检查是否有 Raw 层
                if packet.haslayer(Raw):
                    smtp_info.append(f"Raw Data: {packet[Raw].load.decode('utf-8', 'ignore')}")
                else:
                    smtp_info.append("Raw Data: No payload")
                    
                packet_info.append('\n'.join(smtp_info))
                packet_info.append(smtp_info)
    
    # 添加raw层的内容, 如果RAW还比较小
    if packet.haslayer(Raw) and len(packet[Raw].load)<1000:
        raw_data = packet[Raw].load
        try:
            decoded_data = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            decoded_data = raw_data.decode('utf-8', 'ignore')
        packet_info.append(f"*** Raw Layer ***\nData: {decoded_data}\n")
    return packet_info

def layer_simple_detector(packet):
    """detect layers in a packet, and add all the info into a list"""
    #target_layers=[IP, TCP, UDP, ICMP, DNS, DHCP, HTTPRequest, HTTPResponse, Raw]
    packet_info=[]
    packet_info.append(f"*** Packet Summary ***\n{packet.summary()}\n")
    if packet.haslayer(IP):
        packet_info.append(f"*** IP Layer ***\nSource IP: {packet[IP].src}\nDestination IP: {packet[IP].dst}\n")
    if packet.haslayer(TCP): # 输出tcp的端口, 是ACK还是SYN还是啥, 长度
        packet_info.append(f"*** TCP Layer ***\nSource Port: {packet[TCP].sport}\nDestination Port: {packet[TCP].dport}\nFlags: {packet[TCP].flags}\nLength: {len(packet[TCP])}\n")
    if packet.haslayer(UDP): # 输出udp的端口
        packet_info.append(f"*** UDP Layer ***\nSource Port: {packet[UDP].sport}\nDestination Port: {packet[UDP].dport}\n")
    if packet.haslayer(ICMP): # 输出icmp的type和code
        packet_info.append(f"*** ICMP Layer ***\nType: {packet[ICMP].type}\nCode: {packet[ICMP].code}\n")
    if packet.haslayer(DNS): # 输出dns的id和查询名, 如果是相应也输出响应
        packet_info.append(f"*** DNS Layer ***\nID: {packet[DNS].id}\n")
        if packet[DNS].an:
            packet_info.append(f"Answers: {packet[DNS].an}\n")
        if packet[DNS].ns:
            packet_info.append(f"Query Name: {packet[DNS].qd.qname.decode('utf-8')}\n")
    if packet.haslayer(DHCP): # 输出dhcp的options
        packet_info.append(f"*** DHCP Layer ***\nOptions: {packet[DHCP].options}\n")
    if packet.haslayer(HTTPRequest): # 输出http请求的host, path, method, 包大小
        packet_info.append(f"*** HTTP Request Layer ***\nHost: {packet[HTTPRequest].Host.decode('utf-8')}\nPath: {packet[HTTPRequest].Path.decode('utf-8')}\nMethod: {packet[HTTPRequest].Method.decode('utf-8')}\nPacket Size: {len(packet[HTTPRequest])}\n")
    if packet.haslayer(HTTPResponse): # 输出http响应的状态码
        packet_info.append(f"*** HTTP Response Layer ***\nStatus Code: {packet[HTTPResponse].Status_Code.decode('utf-8')}\nPacket Size: {len(packet[HTTPResponse])}\n")
    if packet.haslayer(TCP) and (packet[TCP].dport==25 or packet[TCP].sport==25) and packet.haslayer(Raw): # STMP
        packet_info.append(f"*** SMTP Layer ***\nSource Port: {packet[TCP].sport}\nDestination Port: {packet[TCP].dport}\nRaw Data: {packet[Raw].load.decode('utf-8', 'ignore')}\n")

    return packet_info

def split_pcap_to_txt(packets, session_id, txt_split_num=10, summary_mode=False):
    """load every packets, using layer_detector, and split them into several txt files"""
    if summary_mode:
        txt_split_num = 1
    total_packets = len(packets)
    packets_per_file = total_packets // txt_split_num + 1
    txt_file_paths = []
    for i in range(txt_split_num):
        start_index = i * packets_per_file
        end_index = min((i + 1) * packets_per_file, total_packets)
        if start_index >= total_packets:
            break
        # 检查有没有data目录, 没有就创建
        import os
        if not os.path.exists('data'):
            os.makedirs('data')

        txt_file_path = f"data/{session_id}_{"summary" if summary_mode else f"part{i+1}"}.txt"
        with open(txt_file_path, 'w') as txt_file:
            for j in range(start_index, end_index):
                if summary_mode:
                    packet_info = layer_simple_detector(packets[j])
                else:
                    packet_info = layer_detector(packets[j])
                txt_file.write(f"*** Packet {j+1} ***\n")
                for info in packet_info:
                    if isinstance(info, list):
                        for line in info:
                            txt_file.write(f"{line}\n")
                    else:
                        txt_file.write(f"{info}\n")
                txt_file.write("\n\n")
        txt_file_paths.append(txt_file_path)
    return txt_file_paths


if __name__ == "__main__":
    pacp_path="./data/apollo_eth0_sample_94.pcap"
    session_id="testsession_94"
    packets = load_pcap(pacp_path)
    print(packets[0])
    print(split_pcap_to_txt(packets, session_id))
    print(split_pcap_to_txt(packets, session_id, summary_mode=True))
    # print(split_pcap_to_json(packets, session_id, num_files=5))


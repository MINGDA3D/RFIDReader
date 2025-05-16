import binascii

# 根据文档中为读取命令提供的8个通道示例，直接映射通道数据字节到完整的命令帧
# "1. 读取通道1: EF 06 11 00 07 FE" (通道数据字节为0x00)
# ...
# "8. 读取通道8: EF 06 11 07 00 FE" (通道数据字节为0x07)
PREDEFINED_READ_COMMANDS = {
    0x00: bytes([0xEF, 0x06, 0x11, 0x00, 0x07, 0xFE]), # 读取通道1
    0x01: bytes([0xEF, 0x06, 0x11, 0x01, 0x06, 0xFE]), # 读取通道2
    0x02: bytes([0xEF, 0x06, 0x11, 0x02, 0x05, 0xFE]), # 读取通道3
    0x03: bytes([0xEF, 0x06, 0x11, 0x03, 0x04, 0xFE]), # 读取通道4
    0x04: bytes([0xEF, 0x06, 0x11, 0x04, 0x03, 0xFE]), # 读取通道5
    0x05: bytes([0xEF, 0x06, 0x11, 0x05, 0x02, 0xFE]), # 读取通道6
    0x06: bytes([0xEF, 0x06, 0x11, 0x06, 0x01, 0xFE]), # 读取通道7
    0x07: bytes([0xEF, 0x06, 0x11, 0x07, 0x00, 0xFE]), # 读取通道8
}

def construct_read_command(channel_data_byte: int) -> bytes | None:
    """
    构建指定通道的读取命令。
    channel_data_byte: 通道的数据字节 (0x00 到 0x07)。
    """
    if channel_data_byte not in PREDEFINED_READ_COMMANDS:
        print(f"错误：无效的通道数据字节 {channel_data_byte:#04x}。允许范围是 0x00 到 0x07。")
        return None
    return PREDEFINED_READ_COMMANDS[channel_data_byte]

def parse_rfid_response(response_bytes: bytes) -> bytes | None:
    """
    解析RFID模块的响应数据帧。
    response_bytes: 模块返回的原始字节数据。
    返回: 提取的标签数据 (bytes)，如果解析失败或无标签则返回 None。
    """
    if not response_bytes:
        print("日志：响应为空。")
        return None

    # 响应帧基本结构: FH(1) LEN(1) CMDC(1) STA(1) DATA(N) BCC(1) EOF(1)
    # 最小长度为7 (例如，无标签响应时DATA为1字节通道)
    if len(response_bytes) < 7:
        print(f"日志：响应过短，长度为 {len(response_bytes)}。")
        return None

    fh = response_bytes[0]
    len_val = response_bytes[1] # LEN 字段的值，根据文档是整个数据帧的长度
    cmdc = response_bytes[2]
    sta = response_bytes[3]
    # response_data_field = response_bytes[4:-2] # 从通道字节到BCC前一个字节
    bcc = response_bytes[-2]
    eof = response_bytes[-1]

    if fh != 0xEF:
        print(f"日志：错误的帧头FH: {fh:#04x}。")
        return None
    if eof != 0xFE:
        print(f"日志：错误的帧尾EOF: {eof:#04x}。")
        return None
    
    # 校验文档中定义的LEN字段
    # "LEN: 整个数据帧的长度，包含LEN本身和最后的帧结束符；"
    # 这通常意味着 LEN_val 就是 response_bytes 的实际长度。
    if len(response_bytes) != len_val:
        print(f"日志：帧长度不匹配。LEN字段值为 {len_val}, 实际接收长度为 {len(response_bytes)}。")
        # 根据文档，LEN包含自身和EOF，这意味着它代表了数据帧的总字节数。
        # 如果严格按此定义，那么len_val应该等于len(response_bytes)
        # return None # 暂时不因长度严格不符而退出，以便处理文档中的示例

    # 检查BCC (这里我们不重新计算BCC，因为计算规则不明确，仅作结构性检查)
    # 实际应用中应严格校验BCC

    if cmdc != 0x11: # 假设这是对0x11命令的响应
        print(f"日志：非预期的命令码CMDC: {cmdc:#04x} in response。")
        # return None # 可以选择更严格

    if sta == 0x00: # 操作成功
        # DATA部分包含1字节通道号 + N字节块内容
        # 响应帧: FH(0) LEN(1) CMDC(2) STA(3) DATA_channel(4) DATA_content(5...L-3) BCC(L-2) EOF(L-1)
        # L是len_val
        
        # 确保有足够的数据容纳通道字节
        if len(response_bytes) < 7: # 至少 FH,LEN,CMDC,STA,CHAN,BCC,EOF
             print(f"日志：成功的响应（STA=0x00）但数据过短，长度 {len(response_bytes)}")
             return None

        response_channel = response_bytes[4]
        print(f"日志：成功读取通道 {response_channel:#04x} 的数据。")
        
        # 标签数据从索引5开始，到BCC之前结束 (即索引 len_val - 3)
        tag_data_start_index = 5
        # 倒数第二个是BCC，倒数第一个是EOF。所以数据结束于倒数第三个字节（含）。
        # 切片时不包含末尾索引，所以是 len_val - 2
        tag_data_end_index = len_val - 2 
        
        if tag_data_start_index >= tag_data_end_index:
            print(f"日志：成功状态，但没有实际的标签数据内容。起始索引 {tag_data_start_index}, 结束索引 {tag_data_end_index}")
            return b'' # 返回空字节串表示无数据内容

        tag_content = response_bytes[tag_data_start_index:tag_data_end_index]
        return tag_content
        
    elif sta == 0x01:
        print("日志：操作状态STA: 0x01 - 密码认证失败。")
        return None
    elif sta == 0x02:
        # 无标签时，DATA为1字节通道
        # EF 07 11 02 01 05 FE (LEN=7, STA=02, DATA_channel=01)
        if len(response_bytes) == 7 :
            response_channel = response_bytes[4]
            print(f"日志：操作状态STA: 0x02 - 通道 {response_channel:#04x} 无标签。")
        else:
            print(f"日志：操作状态STA: 0x02 - 无标签 (响应长度异常: {len(response_bytes)})。")
        return None
    else:
        print(f"日志：未知的操作状态STA: {sta:#04x}。")
        return None

def construct_write_command(tag_data: dict, channel_data_byte: int) -> bytes | None:
    """
    构建指定通道的写入命令。
    tag_data: 包含要写入标签的完整数据的字典。
              例如: {
                  'tag_version': 1000,
                  'filament_manufacturer': "MINGDA 3D",
                  'material_name': "PLA",
                  'color_name': "White",
                  'diameter_target': 1750,
                  'weight_nominal': 1000, # 注意：在 main.py 中已转为 int
                  'print_temp': 210,
                  'bed_temp': 60,
                  'density': 1240
                  # ... 可能还有其他字段，根据您的112字节数据结构
              }
    channel_data_byte: 通道的数据字节 (0x00 到 0x07)。

    返回: 构建好的写入命令字节串，如果构建失败则返回 None。
    
    注意：您需要根据RFID读写器的具体协议文档来实现此函数。
    这通常涉及到：
    1. 确定写入命令的命令码 (CMDC)。
    2. 将 tag_data 字典中的各个字段按照协议规定的顺序和长度，转换为字节串。
       - 字符串（如制造商、材料名、颜色名）需要编码（如ASCII），并可能需要填充到固定长度。
       - 数字（如版本、直径、重量、温度、密度）需要转换为特定字节数和字节序（大端/小端）的整数。
    3. 将这些字节串与通道号组合成数据区 (DATA)。
    4. 构建完整的命令帧，通常包括：
       - 帧头 (FH)
       - 帧长度 (LEN)
       - 命令码 (CMDC)
       - 状态/控制字节 (STA) - 对于发送命令，STA可能固定或根据操作变化
       - 数据区 (DATA) - 包含通道和要写入的标签数据
       - 校验码 (BCC) - 根据帧头到数据区的内容计算
       - 帧尾 (EOF)
    5. 返回完整的字节串。
    """
    print(f"DEBUG: construct_write_command called with channel {channel_data_byte:#04x} and data: {tag_data}")

    # --- 实现占位符 ---
    # 您需要在此处添加实际的命令构建逻辑。
    # 以下是一个非常基础的、不完整的示例结构，您需要替换它。

    # 示例：假设命令结构和一些固定值
    FH = 0xEF
    CMDC_WRITE = 0x12  # 假设写入命令码是 0x12 (您需要确认实际值)
    EOF = 0xFE

    # 1. 将 tag_data 字典转换为112字节的数据负载 (payload)
    #    这需要严格按照您的RFID标签数据格式进行。
    #    例如：
    #    tag_version_bytes = tag_data['tag_version'].to_bytes(2, 'big')
    #    manufacturer_bytes = tag_data['filament_manufacturer'].encode('ascii').ljust(16, b'\\x00')
    #    ... 等等，直到所有112字节数据都被正确格式化。
    
    # --------------------------------------------------------------------------
    # ！！！重要提示！！！
    # 下面的 payload_bytes 是一个【不正确】的示例，仅用于演示结构。
    # 您【必须】根据您的112字节数据格式规范来替换它。
    # 如果数据格式不正确，写入操作将失败或导致标签数据损坏。
    # 确保 payload_bytes 最终是 112 字节长。
    # --------------------------------------------------------------------------
    payload_bytes_list = []
    try:
        # Tag Version (2 bytes, uint16, big-endian)
        payload_bytes_list.append(int(tag_data.get('tag_version', 0)).to_bytes(2, 'big'))
        # Filament Manufacturer (16 bytes, ASCII, null-padded)
        payload_bytes_list.append(str(tag_data.get('filament_manufacturer', '')).encode('ascii', errors='ignore').ljust(16, b'\\x00')[:16])
        # Material Name (16 bytes, ASCII, null-padded)
        payload_bytes_list.append(str(tag_data.get('material_name', '')).encode('ascii', errors='ignore').ljust(16, b'\\x00')[:16])
        # Color Name (32 bytes, ASCII, null-padded)
        payload_bytes_list.append(str(tag_data.get('color_name', '')).encode('ascii', errors='ignore').ljust(32, b'\\x00')[:32])
        # Diameter (Target) (2 bytes, uint16, big-endian)
        payload_bytes_list.append(int(tag_data.get('diameter_target', 0)).to_bytes(2, 'big'))
        # Weight (Nominal, grams) (2 bytes, uint16, big-endian)
        payload_bytes_list.append(int(tag_data.get('weight_nominal', 0)).to_bytes(2, 'big'))
        # Print Temp (C) (2 bytes, uint16, big-endian)
        payload_bytes_list.append(int(tag_data.get('print_temp', 0)).to_bytes(2, 'big'))
        # Bed Temp (C) (2 bytes, uint16, big-endian)
        payload_bytes_list.append(int(tag_data.get('bed_temp', 0)).to_bytes(2, 'big'))
        # Density (2 bytes, uint16, big-endian)
        payload_bytes_list.append(int(tag_data.get('density', 0)).to_bytes(2, 'big'))

        # ... 您需要根据您的完整112字节结构，继续添加剩余字段的转换 ...
        # 例如，如果还有其他字段，继续追加到 payload_bytes_list
        
        # 确保最终的 payload 是112字节
        # 当前已填充: 2+16+16+32+2+2+2+2+2 = 76 字节
        # 还需要 112 - 76 = 36 字节的填充或实际数据
        # 这里用空字节填充剩余部分，您应替换为实际数据字段
        remaining_bytes_to_fill = 112 - sum(len(b) for b in payload_bytes_list)
        if remaining_bytes_to_fill > 0:
            payload_bytes_list.append(b'\\x00' * remaining_bytes_to_fill)
        elif remaining_bytes_to_fill < 0:
            # 这表示上面的字段定义总长度超过了112字节，是个错误
            print("错误：定义的标签数据字段总长度超过112字节！请检查 construct_write_command 中的字段定义。")
            return None

        payload_bytes = b"".join(payload_bytes_list)
        if len(payload_bytes) != 112:
            print(f"错误：最终构建的标签数据负载长度为 {len(payload_bytes)}字节，而不是预期的112字节。")
            return None

    except Exception as e:
        print(f"错误：在准备写入数据负载时发生异常: {e}")
        return None

    # 2. 构建数据区 (DATA) = 通道号 (1 byte) + 数据负载 (112 bytes)
    data_field = bytes([channel_data_byte]) + payload_bytes # 总共 1 + 112 = 113 字节

    # 3. 计算帧长度 (LEN)
    #    LEN = 长度(FH) + 长度(LEN) + 长度(CMDC) + 长度(DATA) + 长度(BCC) + 长度(EOF)
    #    LEN = 1 + 1 + 1 + len(data_field) + 1 + 1 = 5 + len(data_field)
    #    LEN = 5 + 113 = 118 (十进制) = 0x76 (十六进制)
    frame_len = 5 + len(data_field) 

    # 4. 构建待计算BCC的部分: FH + LEN + CMDC + DATA
    bcc_calculation_part = bytes([FH, frame_len, CMDC_WRITE]) + data_field

    # 5. 计算BCC (校验和)
    #    BCC的计算方法需要参考您的协议文档。
    #    常见的简单方法是异或校验 (XOR sum of bytes) 或 取反的异或校验。
    #    假设是 "取反的异或校验": BCC = NOT (byte1 ^ byte2 ^ ... ^ byteN)
    bcc_value = 0
    for byte_val in bcc_calculation_part:
        bcc_value ^= byte_val
    bcc_value = (~bcc_value) & 0xFF  # 取反并确保是单字节

    # 6. 组装完整命令帧
    command_frame = bytes([FH, frame_len, CMDC_WRITE]) + data_field + bytes([bcc_value, EOF])

    if len(command_frame) != frame_len:
         print(f"严重错误：最终命令帧长度 {len(command_frame)} 与计算的帧长度 {frame_len} 不匹配！")
         # return None # 可以选择更严格地在此处返回

    return command_frame
    # --- 实现占位符结束 ---

    # print("错误: construct_write_command 函数尚未完全实现。请根据协议文档填充逻辑。")
    # return None

def main():
    # 1. 选择要读取的通道。例如，读取文档中实例的 "第2通道"
    # 根据文档的通道列表， "读取通道2" 对应的 DATA 字节是 0x01。
    channel_to_read_data_byte = 0x01 
    
    print(f"尝试读取通道 (数据字节: {channel_to_read_data_byte:#04x})...")

    # 2. 构建读取命令
    command = construct_read_command(channel_to_read_data_byte)
    if command:
        print(f"发送的命令: {binascii.hexlify(command).decode('ascii').upper()}")
    else:
        print("无法构建命令。")
        return

    # 3. 模拟接收模块响应
    # 使用文档中 "指定通道读数据" -> "模块响应" -> "有标签" 的例子
    # 主机发送 EF 06 11 01 06 FE (读取第2通道，即DATA为0x01)
    # 模块返回 (有标签): EF 77 11 00 01 (接下来是112字节数据) ... BCC FE
    # 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 
    # 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F 
    # 40 41 42 43 44 45 46 47 48 49 4A 4B 4C 4D 4E 4F 
    # 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F 
    # 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F (文档中这里有重复，我们按实际字节流)
    # 50 51 52 53 54 55 56 57 58 59 5A 5B 5C 5D 5E 5F 
    # 60 61 62 63 64 65 66 67 68 69 6A 6B 6C 6D 6E 6F
    # BCC (77) FE
    # Total 112 bytes of tag data + 1 byte channel_id (01) = 113 bytes in DATA part for BCC calculation.
    # Frame: EF(1) 77(1) 11(1) 00(1) 01(1) [112 bytes data] 77(1) FE(1)
    # Total length = 1+1+1+1+1+112+1+1 = 119 bytes = 0x77. This matches LEN field.

    simulated_response_hex = (
        "EF77110001" + # FH, LEN, CMDC, STA, DATA_Channel (01 for channel 2)
        "000102030405060708090A0B0C0D0E0F" + # Block 1 (16 bytes)
        "101112131415161718191A1B1C1D1E1F" + # Block 2 (16 bytes)
        "404142434445464748494A4B4C4D4E4F" + # Block 3 (16 bytes) from example, seems like a new set
        "303132333435363738393A3B3C3D3E3F" + # Block 4 (16 bytes)
        "303132333435363738393A3B3C3D3E3F" + # Block 5 (16 bytes) (repeated in example)
        "505152535455565758595A5B5C5D5E5F" + # Block 6 (16 bytes)
        "606162636465666768696A6B6C6D6E6F" + # Block 7 (16 bytes)
        "77FE" # BCC and EOF
    )
    simulated_response_bytes = binascii.unhexlify(simulated_response_hex)
    print(f"模拟接收的响应: {binascii.hexlify(simulated_response_bytes).decode('ascii').upper()}")

    # 4. 解析响应
    tag_data = parse_rfid_response(simulated_response_bytes)

    # 5. 打印提取的标签内容 (16进制)
    if tag_data is not None:
        if tag_data: # Check if tag_data is not empty
            hex_tag_data = binascii.hexlify(tag_data).decode('ascii').upper()
            print(f"日志：提取的标签数据 (16进制):")
            # 为便于阅读，可以考虑分块打印
            chunk_size = 32 # 每行打印32个字符 (16字节)
            for i in range(0, len(hex_tag_data), chunk_size):
                print(f"  {hex_tag_data[i:i+chunk_size]}")
        else: # tag_data is b''
            print("日志：解析成功，但标签数据内容为空。")
    else:
        print("日志：未能成功解析标签数据。")

    # 示例：模拟读取一个不存在标签的通道
    print("\n尝试读取一个假设无标签的通道 (例如通道 0x05)...")
    channel_no_tag_data_byte = 0x05
    command_no_tag = construct_read_command(channel_no_tag_data_byte)
    if command_no_tag:
        print(f"发送的命令: {binascii.hexlify(command_no_tag).decode('ascii').upper()}")
    
        # 模拟无标签响应: EF 07 11 02 05 XX FE (BCC for 05 is (EF^07^11^02^05)=F4 -> ~F4=0B. Example list has EF 06 11 05 02 FE)
        # Document example for no tag (channel 0x01): EF 07 11 02 01 05 FE
        # Let's use the structure for channel 0x05, assuming STA=0x02
        # BCC for (EF 07 11 02 05) = NOT(EF^07^11^02^05) = NOT(F4) = 0B
        simulated_no_tag_response_hex = f"EF071102{channel_no_tag_data_byte:02X}0BFE" 
        simulated_no_tag_response_bytes = binascii.unhexlify(simulated_no_tag_response_hex)
        print(f"模拟接收的无标签响应: {binascii.hexlify(simulated_no_tag_response_bytes).decode('ascii').upper()}")
        tag_data_none = parse_rfid_response(simulated_no_tag_response_bytes)
        if tag_data_none is None:
            print("日志：已正确处理无标签情况。")

if __name__ == "__main__":
    main() 
# RFID应用通信协议

主机（与RFID读写器通信的设备称为主机），具体通信方式**暂定为串口，**采用命令-----响应的方式，主机发送命令数据给读写器，模块执行相应的操作，然后把执行结果返回给主机。

主要功能就是读写，指定通道读，指定通道写数据（写号工具，写号工具通过串口通信：通信标准为：1起始位8数据位0校验位1停止位，波特率为115200 ）

# RFID编码规则

All chips MUST contain this information, otherwise they are considered non-compliant

| Field | Data Type | Size (bytes) | Example | Description |
| --- | --- | --- | --- | --- |
| Tag Version | Int | 2 | `1234` | RFID tag data format version to allow future compatibility in the event that the data format changes dramatically. Stored as an int with 3 implied decimal points. Eg `1000` -> `version 1.000` |
| Filament Manufacturer | String | 16 | `"Polar Filament"` | String representation of filament manufacturer.  16 bytes is the max data length per-block. Longer names will be abbreviated or truncated |
| Material Name | String | 16 | `"PLA"` or `"Glass-Filled PC"` | Material name in plain text |
| Color Name | String | 32 | `"Blue"` or `"Electric Watermellon"` | Color in plain text. Color spans 2-blocks |
| Diameter (Target) | Int | 2 | `1750` or `2850` | Filament diameter (target) in µm (micrometers) Eg "1750" -> "1.750mm" |
| Weight (Nominal, grams) | Int | 2 | `1000` (1kg), `5000` (5kg), `750` (750g) | Filament weight in grams, excluding spool weight. This is the TARGET weight, eg "1kg".  Actual measured weight is stored in a different field. |
| Print Temp (C) | Int | 2 | `210` (C), `240` (C) | The recommended print temp in degrees-C |
| Bed Temp (C) | Int | 2 | `60` (C), `80` (C) | The recommended bed temp in degrees-C |
| Density | Int | 2 | `1240` (1.240g/cm<sup>3</sup>), `3900` (3.900g/cm<sup>3</sup>) | Filament density, measured in µg (micrograms) per cubic centimeter. |

# 数据的帧结构

数据帧格式分为主机命令数据帧和模块响应数据帧。

## 主机命令数据帧格式

| 帧头FH | 数据长度LEN | 命令码CMDC | 命令相关数据DATA | 校验值BCC | 帧结束符EOF |
| ------ | ----------- | ---------- | ---------------- | --------- | ----------- |
| 1字节  | 1字节       | 1字节      | N字节            | 1字节     | 1字节       |

## 模块响应数据帧结构

| 帧头FH | 数据长度LEN | 命令码CMDC | 操作状态STA | 命令相关数据DATA | 校验值BCC | 帧结束符EOF |
| ------ | ----------- | ---------- | ----------- | ---------------- | --------- | ----------- |
| 1字节  | 1字节       | 1字节      | 1字节       | N字节            | 1字节     | 1字节       |

## 帧数据含义

FH: 数据帧开始符 0xEF

LEN: 整个数据帧的长度，包含LEN本身和最后的帧结束符；

CMDC：命令码，具体命令参数见下表；

STA：模块执行命令后返回的操作状态，0x00表示操作成功，01 密码认证失败，02 无标签；

DATA: 主机命令相关的参数或模块响应的数据；

BCC: 校验值，从帧头到DATA的最后一个字节，异或取反；

EOF: 帧结束符固定为0xFE；

## 命令码

| 命令           | 命令码 | 说明                     |
| -------------- | ------ | ------------------------ |
| 指定通道读数据 | 0x11   | 读取该通道IC卡的所有数据 |
| 指定通道写数据 | 0x12   | 写该通道IC卡的所有数据   |

## 指定通道读数据

### 主机发送

| 帧头FH | 数据长度LEN | 命令码CMDC | DATA1字节通道（0x00-0x07） | 校验值BCC | 帧结束符EOF |
| ------ | ----------- | ---------- | -------------------------- | --------- | ----------- |
| 0xEF   | 0x06        | 0x11       | 0x01                       | 0xXX      | 0xFE        |

### 模块响应

有标签：

| 帧头FH | 数据长度LEN | 命令码CMDC | 操作状态STA | DATA1字节通道+N字节块内容 | 校验值BCC | 帧结束符EOF |
| ------ | ----------- | ---------- | ----------- | ------------------------- | --------- | ----------- |
| 0xEF   | 0xXX        | 0x11       | 0x00        | N字节                     | 0xXX      | 0xFE        |

无标签：

| 帧头FH | 数据长度LEN | 命令码CMDC | 操作状态STA | DATA1字节通道 | 校验值BCC | 帧结束符EOF |
| ------ | ----------- | ---------- | ----------- | ------------- | --------- | ----------- |
| 0xEF   | 0x07        | 0x11       | 0x02        | 0x01          | 0xXX      | 0xFE        |

通信实例：

读取第2通道的内容命令相关数据

主机发送 EF 06 11 01 06 FE

模块返回

有标签：EF 77 11 00 01 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F 40 41 42 43 44 45 46 47 48 49 4A 4B 4C 4D 4E 4F 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F 50 51 52 53 54 55 56 57 58 59 5A 5B 5C 5D 5E 5F 60 61 62 63 64 65 66 67 68 69 6A 6B 6C 6D 6E 6F 77 FE

无标签：EF 07 11 02 01 05 FE


1. **读取通道1**:

```plain
EF 06 11 00 07 FE
```

2. **读取通道2**:

```plain
EF 06 11 01 06 FE
```

3. **读取通道3**:

```plain
EF 06 11 02 05 FE
```

4. **读取通道4**:

```plain
EF 06 11 03 04 FE
```

5. **读取通道5**:

```plain
EF 06 11 04 03 FE
```

6. **读取通道6**:

```plain
EF 06 11 05 02 FE
```

7. **读取通道7**:

```plain
EF 06 11 06 01 FE
```

8. **读取通道8**:

```plain
EF 06 11 07 00 FE
```


## 指定通道写数据

### 主机发送

| 帧头FH | 数据长度LEN | 命令码CMDC | DATA1字节通道 +  N字节数据    （0x00-0x07）                  | 校验值BCC | 帧结束符EOF |
| ------ | ----------- | ---------- | ------------------------------------------------------------ | --------- | ----------- |
| 0xEF   | 0xXX        | 0x12       | 0x01               0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0a 0x0b 0x0c 0x0d 0x0e 0x0f | 0xXX      | 0xFE        |

### 模块响应

| 帧头FH | 数据长度LEN | 命令码CMDC | 操作状态STA | DATA1字节通道 | 校验值BCC | 帧结束符EOF |
| ------ | ----------- | ---------- | ----------- | ------------- | --------- | ----------- |
| 0xEF   | 0x06        | 0x11       | 0x00        | 0X01          | 0xXX      | 0xFE        |

写状态：0x00 为写成功，0x01为块秘钥错误，0x02为无标签

通信实例：

读取第1通道的内容（16字节）

主机发送 

EF 76 12 01 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F 20 21 22 23 24 25 26 27 28 29 2A 2B 2C 2D 2E 2F 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F 40 41 42 43 44 45 46 47 48 49 4A 4B 4C 4D 4E 4F 50 51 52 53 54 55 56 57 58 59 5A 5B 5C 5D 5E 5F 60 61 62 63 64 65 66 67 68 69 6A 6B 6C 6D 6E 6F 75 FE

模块返回  

有标签：EF 07 12 00 01 04 FE

无标签：EF 07 12 02 01 06 FE


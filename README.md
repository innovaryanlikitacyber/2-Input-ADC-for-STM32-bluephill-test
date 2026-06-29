<div align="center">

# ⚡ Fuzzy Logic Humidity Control — STM32 Blue Pill

### Sistem Kontrol Kelembapan Cerdas Berbasis Logika Fuzzy Sugeno

[![Platform](https://img.shields.io/badge/Platform-STM32F103C8T6-blue?style=for-the-badge&logo=stmicroelectronics&logoColor=white)](https://www.st.com/en/microcontrollers-microprocessors/stm32f103c8.html)
[![Framework](https://img.shields.io/badge/Framework-STM32Cube_HAL-green?style=for-the-badge&logo=stmicroelectronics&logoColor=white)](https://www.st.com/en/embedded-software/stm32cubef1.html)
[![IDE](https://img.shields.io/badge/IDE-PlatformIO-orange?style=for-the-badge&logo=platformio&logoColor=white)](https://platformio.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<br>

> **Supervisor:** Ir. Kemalasari, M.T.
>
> Proyek kontrol cerdas menggunakan logika Fuzzy Sugeno dengan 2 input sensor (suhu & kelembapan) dan 1 output PWM pada mikrokontroler STM32F103C8T6 (Blue Pill).

<br>

</div>

---

## 📋 Daftar Isi

- [Fitur](#-fitur)
- [Spesifikasi Hardware](#-spesifikasi-hardware)
- [Wiring Diagram](#-wiring-diagram)
- [Pin Mapping](#-pin-mapping)
- [Logika Fuzzy Sugeno](#-logika-fuzzy-sugeno)
- [Struktur Proyek](#-struktur-proyek)
- [Cara Instalasi & Upload](#-cara-instalasi--upload)
- [Dashboard IoT](#-dashboard-iot-python-gui)
- [Serial Monitor Output](#-serial-monitor-output)
- [Resource Usage](#-resource-usage)

---

## ✨ Fitur

| Fitur | Deskripsi |
|-------|-----------|
| 🧠 **Fuzzy Sugeno** | 2 input × 3 membership function × 9 rule base |
| 📡 **Dual ADC + DMA** | Pembacaan 2 channel ADC secara simultan via DMA Circular |
| 🔧 **PWM Output** | Kontrol kecepatan buzzer/fan dengan resolusi 8-bit (0–255) |
| 📊 **EMA Filter** | Exponential Moving Average untuk pembacaan ADC yang halus |
| 🔬 **ADC Calibration** | Kalibrasi internal STM32 untuk akurasi penuh hingga 4095 |
| 🖥️ **Dashboard IoT** | GUI Python real-time pengganti serial monitor |
| ⚡ **Efisien** | RAM hanya 2.2% dan Flash 22.5% (framework STM32Cube) |

---

## 🔩 Spesifikasi Hardware

### Mikrokontroler

| Parameter | Spesifikasi |
|-----------|-------------|
| **MCU** | STM32F103C8T6 (Blue Pill) |
| **Arsitektur** | ARM Cortex-M3 |
| **Clock** | 72 MHz (HSE 8 MHz × PLL ×9) |
| **Flash** | 64 KB |
| **SRAM** | 20 KB |
| **ADC** | 12-bit SAR, 2 channel digunakan |
| **Timer** | TIM3 Channel 1 (PWM) |
| **UART** | USART1 (115200 baud) |
| **Tegangan** | 3.3V logic |

### Programmer / Debugger

| Parameter | Spesifikasi |
|-----------|-------------|
| **Debugger** | ST-Link V2.1 |
| **Interface** | SWD (Serial Wire Debug) |
| **Protocol** | Upload via `stlink` |
| **Driver** | STMicroelectronics STLink Virtual COM Port |

### Komponen Pendukung

| Komponen | Jumlah | Fungsi |
|----------|--------|--------|
| Potensiometer 10KΩ | 2 pcs | Simulasi sensor suhu & kelembapan |
| Buzzer / Fan DC | 1 pcs | Aktuator output PWM |
| Kabel Jumper | Secukupnya | Koneksi antar komponen |
| Breadboard | 1 pcs | Prototyping |

---

## 🔌 Wiring Diagram

### ST-Link V2.1 → STM32 Blue Pill (SWD)

```
  ┌─────────────────┐          ┌─────────────────────────┐
  │   ST-Link V2.1  │          │   STM32F103C8 Blue Pill │
  │                 │          │                         │
  │  3.3V ──────────┼──────────┤► 3.3V                   │
  │  GND  ──────────┼──────────┤► GND                    │
  │  SWDIO ─────────┼──────────┤► PA13 (SWDIO)           │
  │  SWCLK ─────────┼──────────┤► PA14 (SWCLK)           │
  │                 │          │                         │
  └─────────────────┘          └─────────────────────────┘
```

### Potensiometer Suhu (PA0)

```
      3.3V
       │
       ┣━━━ Potensio 10KΩ
       │        │
       │        └───────► PA0 (ADC_IN0)
       │
      GND
```

### Potensiometer Kelembapan (PA1)

```
      3.3V
       │
       ┣━━━ Potensio 10KΩ
       │        │
       │        └───────► PA1 (ADC_IN1)
       │
      GND
```

### Buzzer / Fan PWM (PA6)

```
      PA6 (TIM3_CH1)
       │
       └───────► Buzzer (+)
                    │
                   GND
```

### Serial Monitor (USART1)

```
  ┌─────────────────┐          ┌─────────────────────────┐
  │   ST-Link V2.1  │          │   STM32F103C8 Blue Pill │
  │   (Virtual COM) │          │                         │
  │                 │          │                         │
  │  TX  ───────────┼──────────┤► PA10 (USART1_RX)       │
  │  RX  ───────────┼──────────┤► PA9  (USART1_TX)       │
  │                 │          │                         │
  └─────────────────┘          └─────────────────────────┘
```

> **📝 Note:** ST-Link V2.1 sudah memiliki Virtual COM Port bawaan sehingga tidak perlu USB-to-TTL converter tambahan. COM port otomatis muncul sebagai `COMxx` di Device Manager.

---

## 📌 Pin Mapping

### Pin yang Digunakan

| Pin STM32 | Fungsi | Peripheral | Mode | Keterangan |
|-----------|--------|------------|------|------------|
| `PA0` | ADC Input 0 | ADC1_IN0 | Analog | Potensiometer Suhu (0–50 °C) |
| `PA1` | ADC Input 1 | ADC1_IN1 | Analog | Potensiometer Kelembapan (0–100 %) |
| `PA6` | PWM Output | TIM3_CH1 | AF Push-Pull | Buzzer / Fan (~3.9 kHz) |
| `PA9` | UART TX | USART1_TX | AF Push-Pull | Serial Monitor TX → PC |
| `PA10` | UART RX | USART1_RX | Input | Serial Monitor RX ← PC |
| `PA13` | SWD IO | SWDIO | AF | ST-Link Debug/Program |
| `PA14` | SWD CLK | SWCLK | AF | ST-Link Debug/Program |

### Pin Tersedia (Tidak Digunakan)

| Port | Pin Tersedia |
|------|-------------|
| **PA** | PA2, PA3, PA4, PA5, PA7, PA8, PA11, PA12, PA15 |
| **PB** | PB0–PB15 (semua tersedia) |
| **PC** | PC13 (LED onboard), PC14, PC15 |

---

## 🧠 Logika Fuzzy Sugeno

### Arsitektur Sistem

```
                    ┌─────────────────────────────────────────────┐
                    │           FUZZY SUGENO CONTROLLER           │
                    │                                             │
  ┌──────────┐      │   ┌──────────┐   ┌──────────┐   ┌────────┐ │      ┌──────────┐
  │ Pot Suhu │─ADC──┤──►│Fuzzifi-  │──►│  Rule    │──►│Defuzzi-│─┤─PWM─►│ Buzzer / │
  │  (PA0)   │      │   │  kasi    │   │  Base    │   │ fikasi │ │      │   Fan    │
  └──────────┘      │   │          │   │ (9 Rule) │   │  (WA)  │ │      └──────────┘
                    │   │          │   │          │   │        │ │
  ┌──────────┐      │   │          │   │          │   │        │ │
  │ Pot Kel  │─ADC──┤──►│          │──►│          │──►│        │ │
  │  (PA1)   │      │   └──────────┘   └──────────┘   └────────┘ │
  └──────────┘      │                                             │
                    └─────────────────────────────────────────────┘
```

### Membership Function — Input Suhu (0–50 °C)

```
μ(x)
1.0 ┤ ████████████▓▒░               ░▒▓████████████
    │  DINGIN      ▓▒░    NORMAL   ░▒▓     PANAS
    │               ▓▒░   ░▒▓▒░   ░▒▓
    │                ▓▒░ ░▒▓   ▒░ ░▒▓
    │                 ▓▒░▒▓     ▒░▒▓
0.0 ┤──────────────────▓▓──────────▓▓──────────────
    0       20  23  26 27 28  32  36            50  °C
         [trapmf]    [trimf]     [trapmf]
       (0,0,20,26) (23,27,32) (28,36,50,50)
```

### Membership Function — Input Kelembapan (0–100 %)

```
μ(x)
1.0 ┤ ████████████▓▒░               ░▒▓████████████
    │  KERING      ▓▒░    NORMAL   ░▒▓    LEMBAP
    │               ▓▒░   ░▒▓▒░   ░▒▓
    │                ▓▒░ ░▒▓   ▒░ ░▒▓
    │                 ▓▒░▒▓     ▒░▒▓
0.0 ┤──────────────────▓▓──────────▓▓──────────────
    0       40     55 60  65   80               100  %
         [trapmf]    [trimf]     [trapmf]
       (0,0,40,55) (40,60,80) (65,80,100,100)
```

### Rule Base (9 Aturan)

| # | Suhu | Kelembapan | Output PWM | Aksi |
|---|------|------------|------------|------|
| 1 | 🔵 Dingin | 🟤 Kering | `0` | OFF — Tidak perlu pendingin |
| 2 | 🔵 Dingin | 🟢 Normal | `0` | OFF — Kondisi nyaman |
| 3 | 🔵 Dingin | 🔵 Lembap | `128` | SEDANG — Kurangi kelembapan |
| 4 | 🟢 Normal | 🟤 Kering | `0` | OFF — Tidak perlu aksi |
| 5 | 🟢 Normal | 🟢 Normal | `128` | SEDANG — Jaga keseimbangan |
| 6 | 🟢 Normal | 🔵 Lembap | `255` | CEPAT — Kelembapan tinggi |
| 7 | 🔴 Panas | 🟤 Kering | `255` | CEPAT — Suhu kritis |
| 8 | 🔴 Panas | 🟢 Normal | `255` | CEPAT — Suhu kritis |
| 9 | 🔴 Panas | 🔵 Lembap | `255` | CEPAT — Kondisi ekstrem |

### Defuzzifikasi — Weighted Average (Sugeno)

$$
PWM_{output} = \frac{\sum_{i=1}^{9} w_i \times z_i}{\sum_{i=1}^{9} w_i}
$$

Dimana:
- $w_i$ = nilai firing strength rule ke-i (min dari kedua membership)
- $z_i$ = nilai output singleton (0, 128, atau 255)

---

## 📁 Struktur Proyek

```
fuzzy2input2/
├── 📄 platformio.ini          # Konfigurasi PlatformIO
├── 📄 README.md               # Dokumentasi proyek (file ini)
├── 📄 dashboard.py            # GUI Dashboard IoT (Python)
│
├── 📂 src/
│   ├── 📄 main.c              # Program utama (Fuzzy + ADC + PWM)
│   ├── 📄 stm32f1xx_hal_msp.c # Konfigurasi MSP (GPIO, DMA, Clock)
│   ├── 📄 stm32f1xx_it.c      # Interrupt handlers (DMA IRQ)
│   ├── 📄 syscalls.c          # System calls (printf retarget)
│   ├── 📄 sysmem.c            # Memory management
│   └── 📄 system_stm32f1xx.c  # System clock configuration
│
├── 📂 include/                # Header files
├── 📂 lib/                    # External libraries
├── 📂 test/                   # Unit tests
└── 📂 .pio/                   # PlatformIO build output
```

---

## 🚀 Cara Instalasi & Upload

### Prasyarat

| Software | Versi | Link |
|----------|-------|------|
| **VS Code** | Latest | [Download](https://code.visualstudio.com/) |
| **PlatformIO IDE** | Latest | [Extension](https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide) |
| **ST-Link Driver** | V2.1 | [Download](https://www.st.com/en/development-tools/stsw-link009.html) |
| **Python** | 3.8+ | [Download](https://www.python.org/) (untuk Dashboard) |

### Langkah-langkah

**1. Clone Repository**

```bash
git clone https://github.com/username/fuzzy2input2.git
cd fuzzy2input2
```

**2. Buka di VS Code + PlatformIO**

```bash
code .
```

**3. Hubungkan Hardware**

```
ST-Link V2.1  →  Blue Pill (SWD)
   3.3V       →  3.3V
   GND        →  GND
   SWDIO      →  PA13
   SWCLK      →  PA14
```

**4. Build & Upload**

```bash
# Build saja
pio run

# Build + Upload ke board
pio run --target upload

# Monitor Serial
pio device monitor --baud 115200
```

Atau gunakan tombol di VS Code:
- ✅ Build → klik **✓** di status bar
- ⬆️ Upload → klik **→** di status bar
- 🖥️ Monitor → klik **🔌** di status bar

### Konfigurasi PlatformIO

```ini
[env:bluepill_f103c8]
platform    = ststm32
board       = bluepill_f103c8
framework   = stm32cube
upload_protocol = stlink
debug_tool  = stlink
monitor_speed   = 115200
```

---

## 🖥️ Dashboard IoT (Python GUI)

Dashboard real-time pengganti serial monitor dengan tampilan IoT modern.

### Install Dependencies

```bash
pip install pyserial matplotlib
```

### Jalankan Dashboard

```bash
# Default (COM12, 115200 baud)
python dashboard.py

# Custom port
python dashboard.py --port COM5 --baud 115200

# List port tersedia
python dashboard.py --list
```

### Fitur Dashboard

| Fitur | Deskripsi |
|-------|-----------|
| 📊 **5 Gauge Cards** | Suhu, Kelembapan, PWM, RAW ADC CH0, RAW ADC CH1 |
| 📈 **Real-Time Chart** | Grafik scrolling 200 titik data dengan dual Y-axis |
| 🌙 **Dark IoT Theme** | UI modern dark theme dengan accent colors |
| ⚡ **25 FPS** | Refresh GUI setiap 40ms, sangat responsif |
| 🔄 **Auto-reconnect** | Otomatis reconnect jika serial terputus |
| 🟢 **Status Indicator** | Connected / Connecting / Error |

> **⚠️ Penting:** Tutup Serial Monitor PlatformIO terlebih dahulu sebelum menjalankan Dashboard, karena hanya satu program yang bisa mengakses COM port secara bersamaan.

---

## 📺 Serial Monitor Output

```
================================
  Humidity Control - Fuzzy STM32
  Supervisor: Ir. Kemalasari
================================
Suhu:25.3C | Kel:60.2% | PWM:128 | RAW[2078,2466]
Suhu:25.4C | Kel:60.5% | PWM:128 | RAW[2082,2478]
Suhu:30.1C | Kel:75.8% | PWM:255 | RAW[2466,3106]
Suhu:30.2C | Kel:75.9% | PWM:255 | RAW[2474,3110]
Suhu:15.0C | Kel:30.5% | PWM:0   | RAW[1229,1249]
```

### Format Data

```
Suhu:{int}.{dec}C | Kel:{int}.{dec}% | PWM:{0-255} | RAW[{adc0},{adc1}]
```

| Field | Range | Satuan | Keterangan |
|-------|-------|--------|------------|
| Suhu | 0.0 – 50.0 | °C | Dari ADC CH0 × 50/4095 + EMA |
| Kel | 0.0 – 100.0 | % | Dari ADC CH1 × 100/4095 + EMA |
| PWM | 0 – 255 | - | Output Fuzzy Sugeno |
| RAW | 0 – 4095 | LSB | Nilai ADC mentah (12-bit) |

---

## 📊 Resource Usage

### STM32Cube vs Arduino Framework

| Resource | STM32Cube (HAL) | Arduino | Penghematan |
|----------|:---------------:|:-------:|:-----------:|
| **RAM** | 444 B (2.2%) | 1172 B (5.7%) | **62% lebih hemat** |
| **Flash** | 14752 B (22.5%) | 22736 B (34.7%) | **35% lebih hemat** |

### Konfigurasi Peripheral

| Peripheral | Clock | Konfigurasi |
|------------|-------|-------------|
| **System Clock** | 72 MHz | HSE 8 MHz → PLL ×9 |
| **APB1** | 36 MHz | HCLK / 2 (untuk TIM3) |
| **APB2** | 72 MHz | HCLK / 1 (untuk ADC, USART1) |
| **ADC Clock** | 12 MHz | PCLK2 / 6 |
| **ADC Sampling** | 239.5 cycles | ≈ 20 μs per channel |
| **PWM Freq** | ~3.9 kHz | Prescaler=71, Period=255 |
| **UART** | 115200 baud | 8N1, TX+RX |
| **DMA** | Circular | ADC1 → Memory, auto-repeat |

---

## 🛠️ Teknologi & Tools

<div align="center">

| Kategori | Teknologi |
|----------|-----------|
| **Microcontroller** | STM32F103C8T6 (ARM Cortex-M3) |
| **Framework** | STM32Cube HAL |
| **IDE** | VS Code + PlatformIO |
| **Programmer** | ST-Link V2.1 (SWD) |
| **Bahasa** | C (Firmware), Python (Dashboard) |
| **Metode Kontrol** | Logika Fuzzy Sugeno |
| **Dashboard** | Python + Tkinter + Matplotlib |

</div>

---

## 📄 Lisensi

Project ini dibuat untuk keperluan akademis.

**Supervisor:** Ir. Kemalasari, M.T.

---

<div align="center">

**⭐ Jika project ini bermanfaat, berikan bintang di GitHub! ⭐**

Made with ❤️ using STM32 & Fuzzy Logic

</div>
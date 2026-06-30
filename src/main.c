/* USER CODE BEGIN Header */
/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : Humidity Control - Fuzzy Sugeno STM32F103C8
 ******************************************************************************
 * Supervisor: Ir. Kemalasari, M.T.
 * Proyek: Kontrol Cerdas KERENNN
 *
 * Hardware:
 *   PA0 (ADC_IN0) : Potensiometer Suhu       (0-50 C)
 *   PA1 (ADC_IN1) : Potensiometer Kelembapan (0-100 %)
 *   PA6 (TIM3_CH1): Buzzer PWM output
 *   PA9 (USART1_TX): Serial Monitor TX
 *   PA10(USART1_RX): Serial Monitor RX
 ******************************************************************************
 */
/* USER CODE END Header */

#include "main.h"

/* USER CODE BEGIN Includes */
#include <stdio.h>
/* USER CODE END Includes */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
DMA_HandleTypeDef hdma_adc1;
TIM_HandleTypeDef htim3;
UART_HandleTypeDef huart1;

/* USER CODE BEGIN PV */
uint16_t adc_buf[2]; // [0]=suhu raw, [1]=kelembapan raw
uint8_t pwm_out = 0;
uint8_t pwm_lama = 255; // force update pertama

// EMA Filter — alpha kecil = lebih halus, alpha besar = lebih responsif
#define EMA_ALPHA  0.15f
float ema_suhu = 0.0f;   // filtered suhu
float ema_kel  = 0.0f;   // filtered kelembapan
uint8_t ema_init = 0;    // flag inisialisasi pertama
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_ADC1_Init(void);
static void MX_TIM3_Init(void);
static void MX_USART1_UART_Init(void);

/* USER CODE BEGIN PFP */
float trapmf(float x, float a, float b, float c, float d);
float trimf(float x, float a, float b, float c);
float min_val(float a, float b);
float fuzzy_sugeno(float suhu, float kel);
/* USER CODE END PFP */

/* USER CODE BEGIN 0 */

// Retarget printf ke USART1
int __io_putchar(int ch)
{
  HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, HAL_MAX_DELAY);
  return ch;
}

// ── Fungsi keanggotaan ──────────────────────────────────────
float min_val(float a, float b)
{
  return (a < b) ? a : b;
}

float trapmf(float x, float a, float b, float c, float d)
{
  if (x <= a || x >= d)
    return 0.0f;
  if (x >= b && x <= c)
    return 1.0f;
  if (x > a && x < b)
    return (x - a) / (b - a);
  return (d - x) / (d - c);
}

float trimf(float x, float a, float b, float c)
{
  if (x <= a || x >= c)
    return 0.0f;
  if (x == b)
    return 1.0f;
  if (x > a && x < b)
    return (x - a) / (b - a);
  return (c - x) / (c - b);
}

// ── Fuzzy Sugeno ────────────────────────────────────────────
float fuzzy_sugeno(float suhu, float kel)
{
  // Fuzzifikasi Suhu
  float s_dingin = trapmf(suhu, 0.0f, 0.0f, 20.0f, 26.0f);
  float s_normal = trimf(suhu, 23.0f, 27.0f, 32.0f);
  float s_panas = trapmf(suhu, 28.0f, 36.0f, 50.0f, 50.0f);

  // Fuzzifikasi Kelembapan
  float k_kering = trapmf(kel, 0.0f, 0.0f, 40.0f, 55.0f);
  float k_normal = trimf(kel, 40.0f, 60.0f, 80.0f);
  float k_lembap = trapmf(kel, 65.0f, 80.0f, 100.0f, 100.0f);

  // Evaluasi 9 rule + defuzzifikasi weighted average
  float num = 0.0f, den = 0.0f, w;

  // Rule 1: dingin & kering  -> OFF   (0)
  w = min_val(s_dingin, k_kering);
  num += w * 0.0f;
  den += w;
  // Rule 2: dingin & normal  -> OFF   (0)
  w = min_val(s_dingin, k_normal);
  num += w * 0.0f;
  den += w;
  // Rule 3: dingin & lembap  -> SEDANG(128)
  w = min_val(s_dingin, k_lembap);
  num += w * 128.0f;
  den += w;
  // Rule 4: normal & kering  -> OFF   (0)
  w = min_val(s_normal, k_kering);
  num += w * 0.0f;
  den += w;
  // Rule 5: normal & normal  -> SEDANG(128)
  w = min_val(s_normal, k_normal);
  num += w * 128.0f;
  den += w;
  // Rule 6: normal & lembap  -> CEPAT (255)
  w = min_val(s_normal, k_lembap);
  num += w * 255.0f;
  den += w;
  // Rule 7: panas  & kering  -> CEPAT (255)
  w = min_val(s_panas, k_kering);
  num += w * 255.0f;
  den += w;
  // Rule 8: panas  & normal  -> CEPAT (255)
  w = min_val(s_panas, k_normal);
  num += w * 255.0f;
  den += w;
  // Rule 9: panas  & lembap  -> CEPAT (255)
  w = min_val(s_panas, k_lembap);
  num += w * 255.0f;
  den += w;

  if (den == 0.0f)
    return 0.0f;
  return num / den;
}
/* USER CODE END 0 */

int main(void)
{
  HAL_Init();
  SystemClock_Config();

  MX_GPIO_Init();
  MX_DMA_Init();
  MX_ADC1_Init();
  MX_TIM3_Init();
  MX_USART1_UART_Init();

  /* USER CODE BEGIN 2 */
  // Kalibrasi ADC — WAJIB untuk STM32F1 agar akurat sampai 4095
  HAL_ADCEx_Calibration_Start(&hadc1);

  HAL_ADC_Start_DMA(&hadc1, (uint32_t *)adc_buf, 2);
  HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);

  printf("================================\r\n");
  printf("  Humidity Control - Fuzzy STM32\r\n");
  printf("  Supervisor: Ir. Kemalasari\r\n");
  printf("================================\r\n");
  /* USER CODE END 2 */

  while (1)
  {
    /* USER CODE BEGIN 3 */

    // 1. Baca raw ADC + deadzone clamp
    uint16_t raw0 = adc_buf[0];
    uint16_t raw1 = adc_buf[1];
    if (raw0 >= 4090) raw0 = 4095;
    if (raw1 >= 4090) raw1 = 4095;
    if (raw0 <= 15)   raw0 = 0;
    if (raw1 <= 15)   raw1 = 0;

    // 2. Mapping ADC (0-4095) ke satuan fisik
    float suhu_raw = (float)raw0 * 50.0f / 4095.0f;
    float kel_raw  = (float)raw1 * 100.0f / 4095.0f;

    // 3. EMA Filter — pembacaan halus & stabil
    if (!ema_init)
    {
      ema_suhu = suhu_raw;  // inisialisasi langsung pada pembacaan pertama
      ema_kel  = kel_raw;
      ema_init = 1;
    }
    else
    {
      ema_suhu = EMA_ALPHA * suhu_raw + (1.0f - EMA_ALPHA) * ema_suhu;
      ema_kel  = EMA_ALPHA * kel_raw  + (1.0f - EMA_ALPHA) * ema_kel;
    }

    // 4. Hitung fuzzy Sugeno (pakai nilai filtered)
    float hasil = fuzzy_sugeno(ema_suhu, ema_kel);
    pwm_out = (uint8_t)hasil;

    // 5. Update PWM hanya jika berubah (hindari noise)
    if (pwm_out != pwm_lama)
    {
      __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, pwm_out);
      pwm_lama = pwm_out;
    }

    // 6. Kirim ke Serial Monitor (dengan pembulatan benar)
    int s_x10 = (int)(ema_suhu * 10.0f + 0.5f);  // round ke 1 desimal
    int s_int = s_x10 / 10;
    int s_dec = s_x10 % 10;
    int k_x10 = (int)(ema_kel * 10.0f + 0.5f);
    int k_int = k_x10 / 10;
    int k_dec = k_x10 % 10;

    printf("Suhu:%d.%dC | Kel:%d.%d%% | PWM:%d | RAW[%u,%u]\r\n",
       s_int, s_dec, k_int, k_dec, (int)pwm_out,
       raw0, raw1);

    HAL_Delay(20);  // lebih cepat: 20ms (50 Hz)
    /* USER CODE END 3 */
  }
}

/**
 * @brief System Clock Configuration
 */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    Error_Handler();

  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
    Error_Handler();

  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_ADC;
  PeriphClkInit.AdcClockSelection = RCC_ADCPCLK2_DIV6;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
    Error_Handler();
}

/**
 * @brief ADC1 Init — Scan 2 channel + DMA Circular
 */
static void MX_ADC1_Init(void)
{
  ADC_ChannelConfTypeDef sConfig = {0};

  hadc1.Instance = ADC1;
  hadc1.Init.ScanConvMode = ADC_SCAN_ENABLE;
  hadc1.Init.ContinuousConvMode = ENABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 2;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
    Error_Handler();

  // Channel 0 — PA0 — Suhu
  sConfig.Channel = ADC_CHANNEL_0;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SamplingTime = ADC_SAMPLETIME_239CYCLES_5;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
    Error_Handler();

  // Channel 1 — PA1 — Kelembapan
  sConfig.Channel = ADC_CHANNEL_1;
  sConfig.Rank = ADC_REGULAR_RANK_2;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
    Error_Handler();
}

/**
 * @brief TIM3 Init — PWM CH1 di PA6 (Buzzer)
 *        Prescaler=71, Period=255 → freq PWM = 72MHz/72/256 ≈ 3.9kHz
 */
static void MX_TIM3_Init(void)
{
  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};

  htim3.Instance = TIM3;
  htim3.Init.Prescaler = 71;
  htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim3.Init.Period = 255;
  htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_PWM_Init(&htim3) != HAL_OK)
    Error_Handler();

  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim3, &sClockSourceConfig) != HAL_OK)
    Error_Handler();

  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &sMasterConfig) != HAL_OK)
    Error_Handler();

  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  if (HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
    Error_Handler();

  HAL_TIM_MspPostInit(&htim3);
}

/**
 * @brief USART1 Init — 115200 8N1
 */
static void MX_USART1_UART_Init(void)
{
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 115200;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart1) != HAL_OK)
    Error_Handler();
}

/**
 * @brief DMA Init — untuk ADC1
 */
static void MX_DMA_Init(void)
{
  __HAL_RCC_DMA1_CLK_ENABLE();
  HAL_NVIC_SetPriority(DMA1_Channel1_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA1_Channel1_IRQn);
}

/**
 * @brief GPIO Init
 */
static void MX_GPIO_Init(void)
{
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
}

/* USER CODE BEGIN 4 */
/* USER CODE END 4 */

void Error_Handler(void)
{
  __disable_irq();
  while (1)
  {
  }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line) {}
#endif
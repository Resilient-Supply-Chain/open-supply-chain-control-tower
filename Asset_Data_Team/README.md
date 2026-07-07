# Asset Data Team — 数据与模型说明

本目录包含供应链控制塔项目中电力中断预测系统的两个核心模型：**停电风险模型**（Risk Model）与**条件影响预测模型**（Conditional Impact Prediction Model）。两个模型共同构成一套端到端的停电风险与影响评估框架。

---

## 目录结构

```
Asset_Data_Team/
├── risk_model/                          # 停电风险（概率）模型
│   ├── risk_model_score.ipynb           # 模型训练与评估主脚本
│   ├── risk_model_y.ipynb               # 构建目标变量 (Y) 的脚本
│   ├── california_risk_model_data_dec2022_mar2023.csv  # 特征数据 (X)
│   ├── risk_model_y.csv                 # 目标变量数据
│   ├── risk_model_score_predictions.csv # 模型预测输出
│   ├── Risk Model Training Data.xlsx    # 原始训练数据
│   └── eaglei_outage/                   # EAGLE-I 停电原始数据
│       ├── eaglei_outages_with_events_2022.csv
│       ├── eaglei_outages_with_events_2023.csv
│       └── Guideline_OEDI_Updated.docx
│
└── conditional_impact_prediction_model/ # 条件影响预测模型
    ├── conditional_impact_model_poc.ipynb   # 模型训练与评估主脚本
    ├── data_cleaning.ipynb                  # 数据清洗与特征构建脚本
    ├── cleaned_primary_table/
    │   └── conditional_impact_primary_table.csv  # 清洗后的建模数据
    ├── raw_data/                            # 原始数据
    │   ├── california_risk_model_data_dec2022_mar2023.csv  # 天气特征数据
    │   ├── california_risk_model_data_dec2022_mar2023.parquet
    │   ├── eaglei_outages_with_events_2022.csv
    │   └── eaglei_outages_with_events_2023.csv
    ├── risk_predictions_downloaded/
    │   └── risk_model_score_predictions.csv   # 来自风险模型的预测结果
    ├── conditional_impact_xgb_predictions.csv # XGBoost 最终预测输出
    └── combined_risk_and_impact_predictions.csv  # 风险+影响联合预测结果
```

---

## 模型一：停电风险模型（Risk Model）

### 目标

预测加州各县在严重天气事件（大气河、洪涝等）期间发生停电的概率，输出 0–1 的风险评分。

### 数据

| 数据集 | 说明 |
|---|---|
| `california_risk_model_data_dec2022_mar2023.csv` | 2022 年 12 月至 2023 年 3 月加州各县的逐日天气与水文特征，共 7,018 条记录、36 个字段 |
| `eaglei_outages_with_events_2022/2023.csv` | EAGLE-I 历史停电记录，包含事件 ID、州名、县名、停电起止时间、受影响用户数等字段 |
| `risk_model_y.csv` | 目标变量，由停电数据聚合而来，标注各县是否在某日发生停电（1 = 停电，0 = 未停电） |

**主要特征（X）：**

- **大气河（AR）特征**：IVT 最大值、AR 持续时长、AR 类别（AR1–AR4）、7/14 天 AR 累计次数
- **降水指标**：24 小时降水量（`Precip_24h`）、72 小时降水量（`Precip_72h`）、前期降水指数（`API_7d`、`API_14d`）
- **水文指标**：河流流量（`streamflow_mean`）、水位（`gage_height_mean`）、流量百分位、径流比
- **气象极端值**：最大风速、最大风阵速、温度异常、积雪水当量（SWE）
- **前期状态**：10 天降雨天数（`Wet_days_10`）、上次降雨间隔（`Dry_gap`）、是否超过洪水警戒水位

**目标变量（Y）：**

从 EAGLE-I 数据中筛选加州严重天气停电事件，聚合至县-日粒度，停电标记为 1，未停电标记为 0。数据集存在明显类别不平衡（7,018 条中仅 224 条为正例）。

### 方法

1. 将特征数据与目标变量按 `county × date` 合并
2. 使用 **SMOTE** 对少数类（停电事件）进行过采样，缓解类别不平衡
3. 训练并比较 6 种分类模型，以 **Class 1 召回率**为主要优化指标

| 模型 | 准确率 | Class 1 精确率 | Class 1 召回率 | Class 1 F1 |
|---|---|---|---|---|
| Logistic Regression | 0.840 | 0.135 | **0.733** | 0.228 |
| Random Forest | 0.961 | 0.414 | 0.533 | 0.466 |
| Decision Tree | 0.924 | 0.208 | 0.489 | 0.291 |
| XGBoost | 0.956 | 0.356 | 0.467 | 0.404 |
| AdaBoost | 0.927 | 0.204 | 0.444 | 0.280 |
| Gradient Boosting | **0.967** | **0.474** | 0.400 | 0.434 |

> 逻辑回归召回率最高（0.73），但误报率也高；Random Forest 和 Gradient Boosting 在精确率与召回率之间取得更好平衡。

### 输出

`risk_model_score_predictions.csv`：包含每个县-日的实际风险评分（`risk score`）与模型预测风险分数（`predicted_risk_score`，0–1 连续概率值）。

---

## 模型二：条件影响预测模型（Conditional Impact Prediction Model）

### 目标

在**已知停电发生**的前提下，估计受影响的用户总数。这是一个条件回归问题：

> *给定某县某日已发生停电，预测受影响用户数量。*

### 数据

**目标变量（Y）：**

从 EAGLE-I 停电数据中筛选加州 2022 年 12 月至 2023 年 3 月的严重天气事件，按县-日聚合，计算 `total_customers`（每日受影响用户均值之和）。最终共 **224 条正例样本**（即有停电记录的县-日）。

**特征数据（X）：**

与风险模型共享同一份天气与水文特征数据（`california_risk_model_data_dec2022_mar2023.csv`），包含 33 个有效特征（去除 ID 列后）。

**数据清洗流程（`data_cleaning.ipynb`）：**

1. 合并 2022 和 2023 年的 EAGLE-I 停电数据
2. 筛选加州严重天气事件（2022-12 至 2023-03）
3. 按县-日聚合，计算受影响用户总数
4. 与天气特征数据按 `county × date` 内连接，生成建模数据集

### 方法

针对目标值长尾分布和样本量小的特点，对目标变量进行 **log(1 + customers)** 变换，并依次评估两种模型：

#### 1. Ridge 回归（基线）

- 数值特征：中位数填充 + 标准化
- 类别特征（如 `ar_intensity`）：众数填充 + One-Hot 编码
- 使用 **TimeSeriesSplit（4 折）** 进行时序交叉验证

| 折次 | MAE | RMSLE |
|---|---|---|
| Fold 1 | 3,792 | 1.677 |
| Fold 2 | 4,356 | 1.265 |
| Fold 3 | 1,300 | 0.959 |
| Fold 4 | 2,225 | 1.445 |
| **平均** | **2,918** | **1.336** |

#### 2. XGBoost 回归（最终选用）

保守参数设置（`max_depth=3`，`min_child_weight=5`）以防止小样本过拟合，同样使用时序交叉验证评估。

| 指标 | OOF 结果 |
|---|---|
| MAE | **2,194** |
| RMSLE | **1.158** |

XGBoost 在两项指标上均优于 Ridge 回归，被选为最终模型。

### 输出

| 文件 | 说明 |
|---|---|
| `conditional_impact_xgb_predictions.csv` | 每个县-日的实际用户数与 XGBoost 预测用户数 |
| `combined_risk_and_impact_predictions.csv` | 将风险模型预测分数与影响模型预测结果按 `county × date` 合并的联合输出 |

---

## 端到端框架

两个模型的联合输出（`combined_risk_and_impact_predictions.csv`）包含以下字段：

| 字段 | 说明 |
|---|---|
| `county_name` | 加州县名 |
| `date` | 日期 |
| `risk score` | 实际是否发生停电（0/1） |
| `predicted_risk_score` | 风险模型预测的停电概率（0–1） |
| `actual_total_customers` | 实际受影响用户数 |
| `pred_total_customers_xgb` | 条件影响模型预测的受影响用户数 |

**预期使用方式：**

```
预期受影响用户数 ≈ predicted_risk_score × pred_total_customers_xgb
```

通过将停电概率与条件影响规模相乘，可获得各县各日的**无条件预期停电影响**，用于电网应急响应优先级排序。

---

## 模型局限性与后续改进方向

**当前局限：**
- 训练数据仅覆盖加州 2022 年 12 月至 2023 年 3 月，样本量有限（224 条正例）
- 地理粒度为县-日级别，无法捕捉事件内部的空间异质性
- 天气特征与停电时间对齐精度有限

**后续改进方向：**
- 引入其他州或更长时间段的数据以提升泛化能力
- 将粒度细化至馈线级或事件级
- 引入分位数回归或极端值建模以更好地刻画高影响天气事件
- 对风险模型进行概率校准，提升预期影响估算的准确性

# DMHW1：資料探勘作業 1 — 資料轉換與關聯規則前處理

本專案包含資料探勘作業 1 的資料前處理腳本與轉換後的 ARFF 檔案。原始資料來源為 `foodmart.db`（銷售資料）與 `recipe.db`（各國食譜食材資料），透過 Python 腳本將資料轉換為 ARFF 格式，以供 Weka 等工具進行分析（例如關聯規則探勘）。

## 環境需求

- Python 3.8 以上
- 僅使用 Python 標準函式庫（`sqlite3`、`collections`、`math`、`pathlib`、`re`、`itertools`、`os`），不需額外安裝套件

## 專案結構

### 原始資料

| 檔案 | 說明 |
| --- | --- |
| `foodmart.db` | FoodMart SQLite 資料庫（含 `customer`、銷售明細等資料表） |
| `recipe.db` | 食譜 SQLite 資料庫，包含 `Chinese`、`Italian`、`Japanese`、`Thai` 等資料表，每列為「食譜名稱 + 食材」 |
| `italian.arff` | 義大利食譜的 ARFF 原始資料 |

### 轉換腳本

| 腳本 | 功能 | 輸出 |
| --- | --- | --- |
| `q1to2_convert.py` | 讀取 `recipe.db` 的 `Italian` 資料表，將每道食譜轉為一筆交易，每個食材為一個 `{no,yes}` 屬性（稀疏 ARFF 格式） | `Italian_transaction.arff` |
| `q3_convert.py` | 同上，轉換 `Thai` 資料表 | `Thai_transaction.arff` |
| `q4_convert.py` | 讀取 `foodmart.db` 的 `customer` 資料表，進行欄位離散化（收入三分組、子女數與汽車數分組）並輸出二元屬性 | `foodmart_customer_binary.arff` |
| `q5_convert.py` | 讀取 `foodmart.db` 銷售明細，以 `customer_id` + `time_id` + `store_id` 推定交易，並以商品為屬性輸出 | `output_q5/` 目錄 |
| `q6-1_convert.py` | 同 `q1to2_convert.py`，轉換 `Chinese` 資料表 | `Chinese_transaction.arff` |
| `q6-2_convert.py` | 同 `q1to2_convert.py`，轉換 `Japanese` 資料表 | `Japanese_transaction.arff` |
| `check_foodmart_arff.py` | 檢查銷售交易 ARFF 檔案，統計交易數、商品出現次數、商品對共現次數，並檢驗最低支持度 0.1% 下的頻繁項目數量 | 終端機輸出 |

### 轉換結果

| 檔案 | 說明 |
| --- | --- |
| `Chinese_transaction.arff`、`Italian_transaction.arff`、`Japanese_transaction.arff`、`Thai_transaction.arff` | 各國食譜的交易格式資料 |
| `foodmart_customer_binary.arff` | 客戶屬性的二元化資料 |
| `foodmart_sales_jan_nov.arff`、`foodmart_sales_dec.arff` | 銷售交易資料（1–11 月、12 月） |
| `foodmart_sales_jan_nov_temp.arff`、`foodmart_sales_dec_temp.arff` | 中間過程的暫存檔案 |
| `output_q5/` | `q5_convert.py` 的輸出目錄，內含 `foodmart_sales_jan_nov.arff`、`foodmart_sales_dec.arff` |

> 注意：`foodmart_sales_jan_nov.arff` 約 101 MB，超過 GitHub 單一檔案 100 MiB 的上限，因此透過 Git LFS 儲存。

## 使用方式

1. 將本專案 clone 至本機。若要取得大型檔案，請先安裝 [Git LFS](https://git-lfs.com/)：

   ```bash
   git lfs install
   git clone https://github.com/samson8423-job/DMHW1.git
   cd DMHW1
   ```

2. 於專案目錄下執行轉換腳本（腳本以相對路徑讀取資料庫，請在專案根目錄執行）：

   ```bash
   python q1to2_convert.py
   python q3_convert.py
   python q4_convert.py
   python q5_convert.py
   python q6-1_convert.py
   python q6-2_convert.py
   ```

3. 檢查銷售交易檔案：

   ```bash
   python check_foodmart_arff.py
   ```

## ARFF 格式說明

食譜與銷售交易檔案皆採用稀疏（sparse）ARFF 格式：

- 每個屬性皆宣告為 `{no,yes}` 的名義型別。
- 每筆資料以 `{索引 yes, ...}` 表示，未列出的屬性預設為第一個值 `no`。
- 字串值會進行反斜線與單引號的跳脫處理。

## 注意事項

- `q5_convert.py` 的交易識別是以 `customer_id` + `time_id` + `store_id` 推定，並非資料庫原始的訂單編號。
- `q4_convert.py` 的收入離散化切點依據資料分位數（三分位）計算。


import sqlite3
import os
import math
from collections import Counter

# ============================================================
# 1. 基本設定
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "foodmart.db")
OUTPUT_PATH = os.path.join(
    BASE_DIR, "foodmart_customer_binary.arff"
)

TABLE_NAME = "customer"

REQUIRED_COLUMNS = [
    "state_province",
    "yearly_income",
    "gender",
    "total_children",
    "num_children_at_home",
    "education",
    "occupation",
    "houseowner",
    "num_cars_owned",
]


# ============================================================
# 2. 輔助函式
# ============================================================

def is_missing(value):
    if value is None:
        return True

    if isinstance(value, str) and value.strip() == "":
        return True

    return False


def to_number(value):
    if is_missing(value):
        return None

    try:
        number = float(str(value).replace(",", "").strip())

        if math.isfinite(number):
            return number

        return None

    except (ValueError, TypeError):
        return None


def is_numeric_column(values):
    non_missing = [v for v in values if not is_missing(v)]

    if not non_missing:
        return False

    return all(to_number(v) is not None for v in non_missing)


def quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def arff_quote(value):
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace("'", "\\'")
    value = value.replace("\n", " ")
    value = value.replace("\r", " ")

    return "'" + value + "'"


def format_number(value):
    number = to_number(value)

    if number is None:
        return str(value)

    if number.is_integer():
        return str(int(number))

    return str(number)


# ============================================================
# 3. 年收入分組
# ============================================================

def transform_income(values):
    """
    數值收入：依資料分布分為 Low / Medium / High。
    原始文字收入級距：保留原始分類。
    """

    if not is_numeric_column(values):
        result = [
            None if is_missing(v) else str(v).strip()
            for v in values
        ]

        return result, "保留原始文字收入類別"

    numbers = [to_number(v) for v in values]
    valid = sorted(n for n in numbers if n is not None)

    if not valid:
        return [None] * len(values), "沒有有效收入數值"

    def percentile(sorted_values, p):
        position = (len(sorted_values) - 1) * p
        lower = int(math.floor(position))
        upper = int(math.ceil(position))

        if lower == upper:
            return sorted_values[lower]

        weight = position - lower

        return (
            sorted_values[lower] * (1 - weight)
            + sorted_values[upper] * weight
        )

    q1 = percentile(valid, 1 / 3)
    q2 = percentile(valid, 2 / 3)

    result = []

    for number in numbers:
        if number is None:
            result.append(None)
        elif number <= q1:
            result.append("Low")
        elif number <= q2:
            result.append("Medium")
        else:
            result.append("High")

    description = (
        f"收入三分組；切點為 {q1:.2f} 和 {q2:.2f}"
    )

    return result, description


# ============================================================
# 4. 子女人數及汽車數量分組
# ============================================================

def transform_count(value, column):
    number = to_number(value)

    if number is None:
        return None

    number = int(number)

    if column == "total_children":
        if number == 0:
            return "0"
        elif number == 1:
            return "1"
        elif number == 2:
            return "2"
        else:
            return "3_plus"

    if column == "num_children_at_home":
        if number == 0:
            return "0"
        elif number == 1:
            return "1"
        else:
            return "2_plus"

    if column == "num_cars_owned":
        if number == 0:
            return "0"
        elif number == 1:
            return "1"
        else:
            return "2_plus"

    return format_number(value)


# ============================================================
# 5. 讀取 SQLite 資料庫
# ============================================================

if not os.path.exists(DB_PATH):
    raise FileNotFoundError(
        f"找不到資料庫：{DB_PATH}\n"
        "請確認 foodmart.db 與 Python 程式在同一個資料夾。"
    )

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

try:
    tables = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND lower(name)=lower(?)",
        (TABLE_NAME,)
    ).fetchall()

    if not tables:
        raise ValueError("找不到 customer 資料表。")

    actual_table = tables[0]["name"]

    schema = conn.execute(
        f"PRAGMA table_info({quote_identifier(actual_table)})"
    ).fetchall()

    actual_columns = [row["name"] for row in schema]

    column_map = {
        column.lower(): column
        for column in actual_columns
    }

    missing = [
        column for column in REQUIRED_COLUMNS
        if column.lower() not in column_map
    ]

    if missing:
        raise ValueError(
            "資料表缺少欄位：" + ", ".join(missing)
        )

    selected_columns = [
        column_map[column.lower()]
        for column in REQUIRED_COLUMNS
    ]

    sql = (
        "SELECT "
        + ", ".join(
            quote_identifier(column)
            for column in selected_columns
        )
        + " FROM "
        + quote_identifier(actual_table)
    )

    records = conn.execute(sql).fetchall()

finally:
    conn.close()


# ============================================================
# 6. 整理並轉換九個原始欄位
# ============================================================

raw = {}

for column in REQUIRED_COLUMNS:
    actual_name = column_map[column.lower()]

    raw[column] = [
        record[actual_name]
        for record in records
    ]

converted = {}

# 年收入
converted["yearly_income"], income_description = (
    transform_income(raw["yearly_income"])
)

# 數值計數欄位
for column in [
    "total_children",
    "num_children_at_home",
    "num_cars_owned",
]:
    converted[column] = [
        transform_count(value, column)
        for value in raw[column]
    ]

# 類別欄位
for column in [
    "state_province",
    "gender",
    "education",
    "occupation",
    "houseowner",
]:
    converted[column] = [
        None if is_missing(value) else str(value).strip()
        for value in raw[column]
    ]


# ============================================================
# 7. 建立類別清單
# ============================================================

categories = {}

for column in REQUIRED_COLUMNS:
    categories[column] = sorted({
        value
        for value in converted[column]
        if value is not None
    })

    if not categories[column]:
        raise ValueError(
            f"欄位 {column} 沒有有效類別，請檢查原始資料。"
        )


# ============================================================
# 8. 將類別轉成二元屬性
# ============================================================

# 每個屬性名稱代表「某個原始欄位的某個類別」
# 例如：gender=F、gender=M、num_cars_owned=0

binary_attributes = []

for column in REQUIRED_COLUMNS:
    for category in categories[column]:
        attribute_name = f"{column}={category}"
        binary_attributes.append(attribute_name)


# 每一列的每個二元屬性都記錄 yes / no
binary_rows = []

for row_index in range(len(records)):
    row = []

    for column in REQUIRED_COLUMNS:
        actual_value = converted[column][row_index]

        for category in categories[column]:
            if actual_value is None:
                # 原始值缺失時，該欄位的所有類別都標記為缺失
                row.append(None)
            elif actual_value == category:
                row.append("yes")
            else:
                row.append("no")

    binary_rows.append(row)


# ============================================================
# 9. 顯示轉換摘要
# ============================================================

print("=" * 60)
print("Foodmart Customer 二元屬性轉換")
print("=" * 60)

print(f"資料表：{actual_table}")
print(f"顧客筆數：{len(records)}")
print(f"原始欄位數：{len(REQUIRED_COLUMNS)}")
print(f"二元屬性數：{len(binary_attributes)}")
print(f"年收入處理方式：{income_description}")

print("\n各原始欄位的類別數量：")

for column in REQUIRED_COLUMNS:
    print(f"{column}: {len(categories[column])} 類")

print("\n前 10 個二元屬性名稱：")

for attribute in binary_attributes[:10]:
    print(attribute)


# ============================================================
# 10. 輸出 ARFF
# ============================================================

with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
    file.write("@RELATION foodmart_customer_binary\n\n")

    for attribute in binary_attributes:
        file.write(
            f"@ATTRIBUTE {arff_quote(attribute)} "
            "{'no','yes'}\n"
        )

    file.write("\n@DATA\n")

    for row in binary_rows:
        output_values = []

        for value in row:
            if value is None:
                output_values.append("?")
            else:
                output_values.append(arff_quote(value))

        file.write(",".join(output_values) + "\n")


print("\n" + "=" * 60)
print("轉換完成！")
print(f"輸出檔案：{OUTPUT_PATH}")
print(f"Instances：{len(binary_rows)}")
print(f"Attributes：{len(binary_attributes)}")
print("=" * 60)

import sqlite3
import re
from pathlib import Path
from collections import Counter

# =====================================================
# 1. 基本設定
# =====================================================

DB_PATH = Path("foodmart.db")

OUTPUT_DIR = Path("output_q5")
OUTPUT_DIR.mkdir(exist_ok=True)

# 交易識別方式：
# 使用 customer_id + time_id + store_id 作為推定交易識別鍵。
# 注意：這不是資料庫原始訂單編號。
TRANSACTION_COLUMNS = [
    "customer_id",
    "time_id",
    "store_id",
]

# =====================================================
# 2. 工具函式
# =====================================================

def quote_identifier(name):
    """安全引用 SQLite 資料表或欄位名稱。"""
    return '"' + name.replace('"', '""') + '"'


def get_tables(conn):
    sql = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """
    return [
        row[0]
        for row in conn.execute(sql).fetchall()
    ]


def get_columns(conn, table_name):
    sql = f"PRAGMA table_info({quote_identifier(table_name)})"
    return [
        row[1]
        for row in conn.execute(sql).fetchall()
    ]


def find_sales_table(conn, table_name):
    tables = get_tables(conn)

    if table_name not in tables:
        raise ValueError(
            f"找不到資料表 {table_name}。\n"
            f"目前資料庫的資料表：{tables}"
        )

    columns = get_columns(conn, table_name)

    required = {
        "product_id",
        "customer_id",
        "time_id",
        "store_id",
    }

    missing = required - set(columns)

    if missing:
        raise ValueError(
            f"{table_name} 缺少必要欄位：{missing}"
        )

    return table_name


def find_product_table(conn):
    """
    自動尋找包含 product_id 與商品名稱欄位的資料表。

    若找不到，請根據實際資料庫結構修改這個函式。
    """
    tables = get_tables(conn)

    name_candidates = [
        "product_name",
        "product",
        "product_description",
        "product_desc",
        "name",
    ]

    for table in tables:
        columns = get_columns(conn, table)
        lower_map = {
            col.lower(): col
            for col in columns
        }

        if "product_id" not in lower_map:
            continue

        for candidate in name_candidates:
            if candidate in lower_map:
                return (
                    table,
                    lower_map["product_id"],
                    lower_map[candidate],
                )

    return None


def make_attribute_name(product_id, product_name):
    """
    產生 ARFF 欄位名稱。
    加上 product_id，避免不同商品有相同名稱。
    """
    name = str(product_name).strip()
    name = re.sub(r"\s+", " ", name)

    if not name:
        name = f"Product {product_id}"

    return f"product_{product_id}_{name}"


# =====================================================
# 3. 載入商品名稱
# =====================================================

def load_product_names(conn):
    product_table = find_product_table(conn)

    if product_table is None:
        print(
            "\n警告：無法自動找到商品名稱資料表。"
            "\n將先使用 product_id 作為商品名稱。"
        )
        return {}

    table, id_column, name_column = product_table

    sql = f"""
        SELECT
            {quote_identifier(id_column)},
            {quote_identifier(name_column)}
        FROM {quote_identifier(table)}
    """

    rows = conn.execute(sql).fetchall()

    result = {
        row[0]: row[1]
        for row in rows
    }

    print(f"商品名稱資料表：{table}")
    print(f"商品名稱欄位：{name_column}")

    return result


# =====================================================
# 4. 讀取銷售資料
# =====================================================

def load_sales(conn, table_name):
    table_name = find_sales_table(conn, table_name)

    sql = f"""
        SELECT
            product_id,
            customer_id,
            time_id,
            store_id
        FROM {quote_identifier(table_name)}
        WHERE product_id IS NOT NULL
          AND customer_id IS NOT NULL
          AND time_id IS NOT NULL
          AND store_id IS NOT NULL
    """

    rows = conn.execute(sql).fetchall()

    print(f"\n資料表：{table_name}")
    print(f"有效銷售明細筆數：{len(rows):,}")

    return rows


# =====================================================
# 5. 轉換成推定交易
# =====================================================

def build_transactions(rows):
    """
    使用 customer_id + time_id + store_id 分組。
    每筆交易記錄商品集合，避免同一商品重複計數。
    """
    transactions = {}

    for product_id, customer_id, time_id, store_id in rows:
        key = (
            customer_id,
            time_id,
            store_id,
        )

        if key not in transactions:
            transactions[key] = set()

        transactions[key].add(product_id)

    return list(transactions.values())


# =====================================================
# 6. 輸出稀疏 ARFF
# =====================================================

def write_sparse_arff(
    output_path,
    relation_name,
    transactions,
    product_names,
):
    all_products = sorted({
        product_id
        for transaction in transactions
        for product_id in transaction
    })

    product_to_index = {
        product_id: index
        for index, product_id in enumerate(all_products)
    }

    attribute_names = {}

    for product_id in all_products:
        product_name = product_names.get(
            product_id,
            f"Product {product_id}",
        )

        attribute_names[product_id] = make_attribute_name(
            product_id,
            product_name,
        )

    # ARFF 的名目值順序是 f、t。
    # 稀疏格式中省略的欄位預設為第一個值 f。
    with output_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:

        f.write(f"@RELATION {relation_name}\n\n")

        for product_id in all_products:
            name = attribute_names[product_id]

            # 將單引號跳脫，避免商品名稱破壞 ARFF 格式。
            name = name.replace("\\", "\\\\")
            name = name.replace("'", "\\'")

            f.write(
                f"@ATTRIBUTE '{name}' {{f,t}}\n"
            )

        f.write("\n@DATA\n")

        for transaction in transactions:
            indices = sorted(
                product_to_index[product_id]
                for product_id in transaction
            )

            entries = [
                f"{index} t"
                for index in indices
            ]

            f.write(
                "{" + ",".join(entries) + "}\n"
            )

    print(f"ARFF 已輸出：{output_path}")
    print(f"商品屬性數：{len(all_products):,}")
    print(f"推定交易數：{len(transactions):,}")

    if transactions:
        item_counts = [
            len(transaction)
            for transaction in transactions
        ]

        print(f"每筆交易平均商品數：{sum(item_counts) / len(item_counts):.2f}")
        print(f"每筆交易最少商品數：{min(item_counts)}")
        print(f"每筆交易最多商品數：{max(item_counts)}")

    # 額外輸出各商品的交易出現次數
    counts = Counter()

    for transaction in transactions:
        counts.update(transaction)

    print("\n出現次數最多的 10 個商品：")

    for product_id, count in counts.most_common(10):
        print(
            f"{attribute_names[product_id]}："
            f"{count} 筆交易，"
            f"Support={count / len(transactions):.4%}"
        )


# =====================================================
# 7. 主程式
# =====================================================

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"找不到 SQLite 資料庫：{DB_PATH.resolve()}\n"
            "請修改程式最上方的 DB_PATH。"
        )

    with sqlite3.connect(DB_PATH) as conn:
        print("資料庫資料表：")
        print(get_tables(conn))

        product_names = load_product_names(conn)

        # 1～11 月
        jan_nov_rows = load_sales(
            conn,
            "sales_fact_1998",
        )

        jan_nov_transactions = build_transactions(
            jan_nov_rows
        )

        write_sparse_arff(
            OUTPUT_DIR / "foodmart_sales_jan_nov.arff",
            "foodmart_sales_jan_nov",
            jan_nov_transactions,
            product_names,
        )

        # 12 月
        dec_rows = load_sales(
            conn,
            "sales_fact_dec_1998",
        )

        dec_transactions = build_transactions(
            dec_rows
        )

        write_sparse_arff(
            OUTPUT_DIR / "foodmart_sales_dec.arff",
            "foodmart_sales_dec",
            dec_transactions,
            product_names,
        )

    print("\n兩個資料集轉換完成。")


if __name__ == "__main__":
    main()
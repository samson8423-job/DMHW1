from collections import Counter
from itertools import combinations
from pathlib import Path
import re

def check_arff(filename):
    path = Path(filename)

    if not path.exists():
        print(f"找不到檔案：{filename}")
        return

    attributes = []
    transaction_counts = []
    product_counts = Counter()
    pair_counts = Counter()
    total_transactions = 0
    in_data = False

    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("%"):
                continue

            if line.lower() == "@data":
                in_data = True
                continue

            if not in_data:
                if line.lower().startswith("@attribute"):
                    match = re.match(
                        r"@attribute\s+'?([^'\s]+)'?",
                        line,
                        re.IGNORECASE
                    )
                    if match:
                        attributes.append(match.group(1))
                continue

            # 讀取 sparse ARFF 中明確列出的 yes
            total_transactions += 1
            products = []

            if line.startswith("{") and line.endswith("}"):
                content = line[1:-1].strip()

                if content:
                    entries = re.findall(
                        r"(\d+)\s+'([^']+)'",
                        content
                    )

                    for index_text, value in entries:
                        if value == "yes":
                            index = int(index_text)

                            if index >= len(attributes):
                                raise ValueError(
                                    f"屬性索引超出範圍：{index}"
                                )

                            product = attributes[index]
                            products.append(product)
                            product_counts[product] += 1

            transaction_counts.append(len(products))

            # 統計同一筆交易內的兩兩商品組合
            for a, b in combinations(sorted(set(products)), 2):
                pair_counts[(a, b)] += 1

    print("\n" + "=" * 60)
    print(f"檔案：{filename}")
    print(f"商品屬性數：{len(attributes)}")
    print(f"交易數：{total_transactions}")
    print(f"商品出現總次數：{sum(product_counts.values())}")

    if transaction_counts:
        print(f"每筆交易商品數最少：{min(transaction_counts)}")
        print(f"每筆交易商品數最多：{max(transaction_counts)}")
        print(
            f"每筆交易平均商品數："
            f"{sum(transaction_counts) / len(transaction_counts):.2f}"
        )

    print("\n出現次數最多的 15 個商品：")
    for product, count in product_counts.most_common(15):
        support = count / total_transactions
        print(
            f"{product}: {count} 筆交易，"
            f"Support={support:.4%}"
        )

    print("\n共同出現次數最多的 15 組商品：")
    for (a, b), count in pair_counts.most_common(15):
        support = count / total_transactions
        print(
            f"{a} + {b}: {count} 筆交易，"
            f"Support={support:.4%}"
        )

    # 檢查支持度 0.1% 下，是否存在頻繁商品對
    min_support = 0.001
    min_count = total_transactions * min_support

    frequent_pairs = [
        (pair, count)
        for pair, count in pair_counts.items()
        if count / total_transactions >= min_support
    ]

    print(f"\n支持度門檻：{min_support:.2%}")
    print(f"達到支持度門檻的商品對數量：{len(frequent_pairs)}")
    print(f"理論上的最低共同出現次數：{min_count:.2f}")

    # 依照實際資料，統計至少符合最低支持度的單一商品數量
    frequent_products = [
        (product, count)
        for product, count in product_counts.items()
        if count / total_transactions >= min_support
    ]

    print(f"達到支持度門檻的單一商品數量：{len(frequent_products)}")


check_arff("foodmart_sales_jan_nov.arff")
check_arff("foodmart_sales_dec.arff")
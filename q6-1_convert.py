import sqlite3
from collections import defaultdict

DB_FILE = "recipe.db"
TABLE_NAME = "Chinese"
OUTPUT_FILE = "Chinese_transaction.arff"

def arff_quote(value):
    """Quote an ARFF string and escape backslashes/single quotes."""
    value = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return "'" + value + "'"

# 1. Read the original recipe-ingredient rows from SQLite
conn = sqlite3.connect(DB_FILE)
try:
    rows = conn.execute(
        f'SELECT recipe_name, ingredient FROM "{TABLE_NAME}"'
    ).fetchall()
finally:
    conn.close()

# 2. Group ingredients by recipe name; remove blank values and duplicates
recipe_ingredients = defaultdict(set)

for recipe_name, ingredient in rows:
    if recipe_name is None or ingredient is None:
        continue

    recipe_name = str(recipe_name).strip()
    ingredient = str(ingredient).strip()

    if recipe_name and ingredient:
        recipe_ingredients[recipe_name].add(ingredient)

# 3. Create a stable ingredient-to-attribute index
ingredients = sorted({
    ingredient
    for ingredient_set in recipe_ingredients.values()
    for ingredient in ingredient_set
})
ingredient_index = {ingredient: i for i, ingredient in enumerate(ingredients)}

# 4. Write an ARFF file:
#    one instance per recipe, one nominal attribute per ingredient.
#    In sparse ARFF, omitted attributes use their first value: "no".
with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.write("% Chinese recipes transformed into transaction format\n")
    f.write("@RELATION Chinese_transaction\n\n")

    for ingredient in ingredients:
        f.write(f"@ATTRIBUTE {arff_quote(ingredient)} {{no,yes}}\n")

    f.write("\n@DATA\n")

    for recipe_name in sorted(recipe_ingredients):
        present_indices = sorted(
            ingredient_index[ingredient]
            for ingredient in recipe_ingredients[recipe_name]
        )
        # Only list ingredients present in this recipe ("yes").
        sparse_values = ", ".join(f"{i} yes" for i in present_indices)
        f.write("{" + sparse_values + "}\n")

print("轉換成功！")
print(f"輸出檔案：{OUTPUT_FILE}")
print(f"原始明細筆數：{len(rows):,}")
print(f"食譜交易筆數：{len(recipe_ingredients):,}")
print(f"食材屬性數量：{len(ingredients):,}")

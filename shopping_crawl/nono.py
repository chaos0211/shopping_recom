from sqlalchemy import create_engine, text

# 数据库连接配置

db_config = {
    'host': 'localhost',
    'port': 33309,
    'user': 'root',
    'password': '123456',
    'database': 'shopping_spark'
}

# 构建数据库连接字符串
url = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}?charset=utf8mb4"
engine = create_engine(url)

with engine.begin() as conn:
    # 创建 categories 表（如果不存在）
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) UNIQUE
        );
    """))

    # 插入唯一分类
    conn.execute(text("""
        INSERT IGNORE INTO categories (name)
        SELECT DISTINCT category FROM tmall_products
        WHERE category IS NOT NULL AND category != '';
    """))

    # 插入 products 表内容，添加 merchant_id 常量值 1
    conn.execute(text("""
        INSERT INTO products (item_id, name, price, image_url, category_id, merchant_id)
        SELECT 
            tp.item_id,
            tp.name,
            CAST(CASE 
                     WHEN tp.price REGEXP '^[0-9]+(\\.[0-9]{1,2})?$' THEN tp.price
                     ELSE '0.00'
                 END AS DECIMAL(10,2)),
            tp.local_image_path,
            c.id,
            1
        FROM tmall_products tp
        JOIN categories c ON tp.category = c.name
        WHERE tp.item_id IS NOT NULL 
          AND tp.name IS NOT NULL
    """))

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.functions import countDistinct
from pyspark.sql.types import *
import pandas as pd
import os


class DataPreprocessor:
    def __init__(self, app_name="DataPreprocessor"):
        jar_path = os.path.abspath("app/cli/mysql-connector-j-8.0.33.jar")

        self.spark = SparkSession.builder \
            .appName(app_name) \
            .master("local[*]") \
            .config("spark.jars", jar_path) \
            .getOrCreate()

    def get_interactions_data(self):
        """从数据库加载并生成用户-商品交互矩阵"""
        from app.models.user import User
        from app.models.order import Order, OrderItem
        from app.models.review import Review
        from app import db

        mysql_config = {
            'url': f"jdbc:mysql://{db.engine.url.host}:{db.engine.url.port}/{db.engine.url.database}?useSSL=false&serverTimezone=UTC",
            'user': db.engine.url.username,
            'password': db.engine.url.password
        }

        users_df = self.load_data_from_mysql("users", mysql_config)
        orders_df = self.load_data_from_mysql("orders", mysql_config)
        order_items_df = self.load_data_from_mysql("order_items", mysql_config)
        reviews_df = self.load_data_from_mysql("reviews", mysql_config)
        browsing_df = self.load_data_from_mysql("browsing_history", mysql_config)
        favorites_df = self.load_data_from_mysql("favorites", mysql_config)
        cart_items_df = self.load_data_from_mysql("cart", mysql_config)

        interactions_df = self.preprocess_interaction_data(
            orders_df, order_items_df, reviews_df,
            browsing_df, favorites_df, cart_items_df
        )
        user_item_matrix = self.create_user_item_matrix(interactions_df)

        return user_item_matrix

    def load_data_from_mysql(self, table_name, mysql_config):
        """从MySQL加载数据"""
        df = self.spark.read \
            .format("jdbc") \
            .option("url", mysql_config['url']) \
            .option("dbtable", table_name) \
            .option("user", mysql_config['user']) \
            .option("password", mysql_config['password']) \
            .option("driver", "com.mysql.cj.jdbc.Driver") \
            .load()
        return df

    def preprocess_user_data(self, users_df):
        """预处理用户数据"""
        # 添加用户特征
        processed_df = users_df.withColumn(
            "user_age_days",
            datediff(current_date(), col("created_at"))
        ).withColumn(
            "user_segment",
            when(col("user_age_days") < 30, "new")
            .when(col("user_age_days") < 180, "regular")
            .otherwise("loyal")
        )
        return processed_df

    def preprocess_interaction_data(self, orders_df, order_items_df, reviews_df, browsing_df, favorites_df, cart_items_df):
        """预处理交互数据"""
        # 合并订单和订单项
        order_interactions = orders_df.alias("o").join(
            order_items_df.alias("oi"),
            col("o.id") == col("oi.order_id")
        ).select(
            col("o.user_id"),
            col("oi.product_id"),
            col("oi.quantity"),
            col("oi.price"),
            col("o.created_at").alias("interaction_date"),
            lit("purchase").alias("interaction_type")
        )

        # 处理评价数据
        review_interactions = reviews_df.select(
            col("user_id"),
            col("product_id"),
            col("rating").alias("quantity"),
            lit(0).alias("price"),
            col("created_at").alias("interaction_date"),
            lit("review").alias("interaction_type")
        )

        # 浏览行为
        browsing_interactions = browsing_df.select(
            col("user_id"),
            col("product_id"),
            lit(1).alias("quantity"),
            lit(0).alias("price"),
            col("timestamp").alias("interaction_date"),
            lit("browse").alias("interaction_type")
        )

        # 收藏行为
        favorite_interactions = favorites_df.select(
            col("user_id"),
            col("product_id"),
            lit(1).alias("quantity"),
            lit(0).alias("price"),
            col("created_at").alias("interaction_date"),
            lit("favorite").alias("interaction_type")
        )

        # 购物车行为
        cart_interactions = cart_items_df.select(
            col("user_id"),
            col("product_id"),
            col("quantity"),
            lit(0).alias("price"),
            col("added_at").alias("interaction_date"),
            lit("cart").alias("interaction_type")
        )

        # 合并所有交互数据
        all_interactions = order_interactions.union(review_interactions) \
            .union(browsing_interactions) \
            .union(favorite_interactions) \
            .union(cart_interactions)

        return all_interactions

    def create_user_item_matrix(self, interactions_df):
        """创建用户-物品矩阵"""
        # 计算隐式反馈分数，加入各行为权重
        user_item_scores = interactions_df.groupBy("user_id", "product_id").agg(
            sum(
                when(col("interaction_type") == "purchase", col("quantity") * 5)
                .when(col("interaction_type") == "review", col("quantity") * 4)
                .when(col("interaction_type") == "cart", col("quantity") * 2)
                .when(col("interaction_type") == "favorite", col("quantity") * 3)
                .when(col("interaction_type") == "browse", col("quantity") * 1)
                .otherwise(1)
            ).alias("score"),
            max("interaction_date").alias("last_interaction")
        )

        # 时间衰减
        user_item_scores = user_item_scores.withColumn(
            "time_decay",
            exp(-datediff(current_date(), col("last_interaction")) / 30.0)
        ).withColumn(
            "final_score",
            col("score") * col("time_decay")
        )

        return user_item_scores

    def get_product_features(self, products_df, interactions_df):
        """提取商品特征"""
        # 计算商品统计特征
        product_stats = interactions_df.filter(
            col("interaction_type") == "purchase"
        ).groupBy("product_id").agg(
            count("*").alias("purchase_count"),
            sum("quantity").alias("total_sold"),
            countDistinct("user_id").alias("unique_buyers")
        )

        # 合并商品基本信息和统计特征
        product_features = products_df.alias("p").join(
            product_stats.alias("ps"),
            col("p.id") == col("ps.product_id"),
            "left"
        ).select(
            col("p.*"),
            coalesce(col("ps.purchase_count"), lit(0)).alias("purchase_count"),
            coalesce(col("ps.total_sold"), lit(0)).alias("total_sold"),
            coalesce(col("ps.unique_buyers"), lit(0)).alias("unique_buyers")
        )

        return product_features

    def close(self):
        """关闭Spark会话"""
        self.spark.stop()
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
from pyspark.ml.feature import StringIndexer
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql.functions import *
import numpy as np
from pyspark.sql.functions import countDistinct


class RecommendationEngine:
    def __init__(self, app_name="RecommendationEngine"):
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .master("local[*]") \
            .getOrCreate()
        self.model = None
        self.user_indexer = None
        self.item_indexer = None

    def prepare_training_data(self, user_item_scores_df):
        """准备训练数据"""
        # 为用户和物品创建数值索引
        self.user_indexer = StringIndexer(
            inputCol="user_id",
            outputCol="user_index"
        ).fit(user_item_scores_df)

        self.item_indexer = StringIndexer(
            inputCol="product_id",
            outputCol="item_index"
        ).fit(user_item_scores_df)

        # 转换数据
        indexed_df = self.user_indexer.transform(user_item_scores_df)
        indexed_df = self.item_indexer.transform(indexed_df)

        return indexed_df.select("user_index", "item_index", "final_score")

    def train_als_model(self, training_data, rank=10, maxIter=20, regParam=0.1):
        """训练ALS协同过滤模型"""
        als = ALS(
            maxIter=maxIter,
            regParam=regParam,
            rank=rank,
            userCol="user_index",
            itemCol="item_index",
            ratingCol="final_score",
            coldStartStrategy="drop",
            implicitPrefs=True
        )

        self.model = als.fit(training_data)
        return self.model

    def evaluate_model(self, test_data):
        """评估模型性能"""
        predictions = self.model.transform(test_data)
        evaluator = RegressionEvaluator(
            metricName="rmse",
            labelCol="final_score",
            predictionCol="prediction"
        )
        rmse = evaluator.evaluate(predictions)
        return rmse

    def get_user_recommendations(self, user_id, num_recommendations=10):
        """为特定用户获取推荐"""
        if not self.model:
            raise ValueError("模型尚未训练")

        # 获取用户索引
        user_df = self.spark.createDataFrame([(user_id,)], ["user_id"])
        user_indexed = self.user_indexer.transform(user_df)
        user_index = user_indexed.collect()[0]["user_index"]

        # 获取推荐
        user_subset = self.spark.createDataFrame([(int(user_index),)], ["user_index"])
        recommendations = self.model.recommendForUserSubset(
            user_subset,
            num_recommendations
        )

        # 转换回原始ID
        rec_list = recommendations.collect()[0]["recommendations"]
        item_indices = [rec["item_index"] for rec in rec_list]
        scores = [rec["rating"] for rec in rec_list]

        # 反向转换物品索引
        item_df = self.spark.createDataFrame(
            [(float(idx),) for idx in item_indices],
            ["item_index"]
        )

        # 获取原始物品ID
        item_mapping = self.item_indexer.labels
        recommendations_with_ids = []

        for i, (item_idx, score) in enumerate(zip(item_indices, scores)):
            product_id = int(float(item_mapping[int(item_idx)]))
            recommendations_with_ids.append({
                'product_id': product_id,
                'score': float(score),
                'rank': i + 1
            })

        return recommendations_with_ids

    def get_similar_items(self, product_id, num_similar=10):
        """获取相似商品"""
        if not self.model:
            raise ValueError("模型尚未训练")

        # 获取物品索引
        item_df = self.spark.createDataFrame([(product_id,)], ["product_id"])
        item_indexed = self.item_indexer.transform(item_df)
        item_index = item_indexed.collect()[0]["item_index"]

        # 获取相似物品
        item_subset = self.spark.createDataFrame([(int(item_index),)], ["item_index"])
        similar_items = self.model.recommendForItemSubset(
            item_subset,
            num_similar
        )

        # 处理结果
        similar_list = similar_items.collect()[0]["recommendations"]
        item_mapping = self.user_indexer.labels

        similar_with_ids = []
        for i, rec in enumerate(similar_list):
            user_id = int(float(item_mapping[int(rec["user_index"])]))
            similar_with_ids.append({
                'user_id': user_id,
                'similarity_score': float(rec["rating"]),
                'rank': i + 1
            })

        return similar_with_ids

    def get_popular_items(self, interactions_df, num_items=10):
        """获取热门商品推荐"""
        popular_items = interactions_df.filter(
            col("interaction_type") == "purchase"
        ).groupBy("product_id").agg(
            count("*").alias("interaction_count"),
            countDistinct("user_id").alias("unique_users"),
            avg("final_score").alias("avg_score")
        ).withColumn(
            "popularity_score",
            col("interaction_count") * col("unique_users") * col("avg_score")
        ).orderBy(col("popularity_score").desc()).limit(num_items)

        return popular_items.collect()

    def close(self):
        """关闭Spark会话"""
        self.spark.stop()
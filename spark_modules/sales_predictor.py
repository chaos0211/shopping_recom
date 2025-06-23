from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.regression import LinearRegression, RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql.functions import *
from pyspark.sql.functions import countDistinct
from pyspark.sql.types import *


class SalesPredictor:
    def __init__(self, app_name="SalesPredictor"):
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .master("local[*]") \
            .getOrCreate()
        self.model = None
        self.feature_assembler = None
        self.scaler = None

    def prepare_sales_features(self, products_df, interactions_df):
        """准备销售预测特征"""
        # 计算历史销售统计
        sales_stats = interactions_df.filter(
            col("interaction_type") == "purchase"
        ).groupBy("product_id").agg(
            sum("quantity").alias("total_sales"),
            count("*").alias("order_count"),
            countDistinct("user_id").alias("unique_customers"),
            avg("quantity").alias("avg_order_quantity"),
            stddev("quantity").alias("sales_volatility")
        )

        # 计算时间趋势特征
        recent_sales = interactions_df.filter(
            (col("interaction_type") == "purchase") &
            (col("interaction_date") >= date_sub(current_date(), 30))
        ).groupBy("product_id").agg(
            sum("quantity").alias("recent_30d_sales"),
            count("*").alias("recent_30d_orders")
        )

        # 合并特征
        features_df = products_df.alias("p").join(
            sales_stats.alias("ss"),
            col("p.id") == col("ss.product_id"),
            "left"
        ).join(
            recent_sales.alias("rs"),
            col("p.id") == col("rs.product_id"),
            "left"
        )

        # 填充缺失值并创建新特征
        features_df = features_df.fillna(0).withColumn(
            "price_category",
            when(col("price") < 50, 1)
            .when(col("price") < 200, 2)
            .otherwise(3)
        ).withColumn(
            "sales_momentum",
            coalesce(col("recent_30d_sales"), lit(0)) /
            (coalesce(col("total_sales"), lit(1)) + 1)
        ).withColumn(
            "customer_loyalty",
            coalesce(col("unique_customers"), lit(0)) /
            (coalesce(col("order_count"), lit(1)) + 1)
        )

        return features_df

    def create_training_data(self, features_df, target_days=30):
        """创建训练数据集"""
        # 这里简化处理，实际应该用时间序列分割
        # 目标变量：预测未来30天的销量
        training_data = features_df.withColumn(
            "target_sales",
            coalesce(col("recent_30d_sales"), lit(0))
        ).withColumn(
            "days_since_creation",
            datediff(current_date(), col("created_at"))
        )

        return training_data

    def prepare_features_for_ml(self, training_data):
        """准备机器学习特征"""
        feature_cols = [
            "price", "stock", "category_id", "total_sales",
            "order_count", "unique_customers", "avg_order_quantity",
            "sales_volatility", "recent_30d_sales", "recent_30d_orders",
            "price_category", "sales_momentum", "customer_loyalty",
            "days_since_creation"
        ]

        # 组装特征向量
        self.feature_assembler = VectorAssembler(
            inputCols=feature_cols,
            outputCol="features_raw"
        )

        assembled_data = self.feature_assembler.transform(training_data)

        # 特征标准化
        self.scaler = StandardScaler(
            inputCol="features_raw",
            outputCol="features",
            withStd=True,
            withMean=True
        ).fit(assembled_data)

        scaled_data = self.scaler.transform(assembled_data)

        return scaled_data.select("features", "target_sales")

    def train_prediction_model(self, training_data, model_type="linear"):
        """训练销售预测模型"""
        if model_type == "linear":
            self.model = LinearRegression(
                featuresCol="features",
                labelCol="target_sales",
                regParam=0.1,
                elasticNetParam=0.1
            )
        elif model_type == "rf":
            self.model = RandomForestRegressor(
                featuresCol="features",
                labelCol="target_sales",
                numTrees=20,
                maxDepth=10
            )

        self.model = self.model.fit(training_data)
        return self.model

    def predict_sales(self, products_df):
        """预测商品销量"""
        if not self.model:
            raise ValueError("模型尚未训练")

        # 准备预测数据
        prepared_data = self.feature_assembler.transform(products_df)
        scaled_data = self.scaler.transform(prepared_data)

        # 进行预测
        predictions = self.model.transform(scaled_data)

        return predictions.select(
            "id",
            "name",
            "price",
            "prediction"
        ).withColumnRenamed("prediction", "predicted_sales")

    def evaluate_model(self, test_data):
        """评估模型性能"""
        predictions = self.model.transform(test_data)

        evaluator = RegressionEvaluator(
            labelCol="target_sales",
            predictionCol="prediction",
            metricName="rmse"
        )
        rmse = evaluator.evaluate(predictions)

        evaluator_r2 = RegressionEvaluator(
            labelCol="target_sales",
            predictionCol="prediction",
            metricName="r2"
        )
        r2 = evaluator_r2.evaluate(predictions)

        return {"rmse": rmse, "r2": r2}

    def get_sales_insights(self, predictions_df):
        """获取销售洞察"""
        insights = predictions_df.agg(
            avg("predicted_sales").alias("avg_predicted_sales"),
            max("predicted_sales").alias("max_predicted_sales"),
            min("predicted_sales").alias("min_predicted_sales"),
            stddev("predicted_sales").alias("sales_std")
        ).collect()[0]

        top_products = predictions_df.orderBy(
            col("predicted_sales").desc()
        ).limit(10).collect()

        return {
            "overall_stats": insights.asDict(),
            "top_predicted_products": [row.asDict() for row in top_products]
        }

    def close(self):
        """关闭Spark会话"""
        self.spark.stop()
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'mysql+pymysql://root:123456@localhost:33309/shopping_spark'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Spark配置
    SPARK_APP_NAME = "ShoppingRecommendation"
    SPARK_MASTER = "local[*]"

    # 推荐系统参数
    RECOMMENDATION_COUNT = 10
    MIN_RATING = 1
    MAX_RATING = 5
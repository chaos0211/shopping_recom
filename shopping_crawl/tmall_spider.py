import time
import os
import json
import requests
import mysql.connector
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import urllib.parse
from PIL import Image
import io

Base = declarative_base()


class Product(Base):
    __tablename__ = 'tmall_products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(50), unique=True, nullable=False)  # 新增商品id字段
    name = Column(String(500), nullable=False)
    price = Column(Float)
    image_url = Column(Text)
    local_image_path = Column(String(500))
    shop_name = Column(String(200))
    shop_rating = Column(String(50))
    category = Column(String(100))
    crawled_at = Column(DateTime, default=datetime.now)


class TmallCrawler:
    def __init__(self, db_config, image_dir="./images"):
        """
        初始化爬虫

        Args:
            db_config: 数据库配置字典
            image_dir: 图片保存目录
        """
        self.db_config = db_config
        self.image_dir = image_dir
        self.driver = None
        self.session = None
        self.cookies_file = "tmall_cookies.json"

        # 创建图片目录
        os.makedirs(self.image_dir, exist_ok=True)

        # 初始化数据库
        self.init_database()

    def init_database(self):
        """初始化数据库连接和表结构"""
        try:
            # 创建数据库引擎
            engine_url = f"mysql+pymysql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            self.engine = create_engine(engine_url, echo=False)

            # 创建表
            Base.metadata.create_all(self.engine)

            # 创建会话
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

            print("数据库连接成功！")
        except Exception as e:
            print(f"数据库连接失败: {e}")
            raise

    def init_driver(self):
        """初始化Chrome驱动"""
        try:
            chrome_options = Options()
            # 设置User-Agent
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            # 禁用图片加载以提高速度（可选）
            # chrome_options.add_argument("--blink-settings=imagesEnabled=false")
            # 禁用通知
            chrome_options.add_argument("--disable-notifications")
            # 设置窗口大小
            chrome_options.add_argument("--window-size=1920,1080")
            # 禁用无头模式，确保扫码登录二维码可以正常显示
            # chrome_options.add_argument("--headless")  # 无头，注释掉，避免异步内容无法渲染

            # 在macOS上，通常Chrome驱动在PATH中
            from selenium.webdriver.chrome.service import Service

            chrome_driver_path = "shopping_crawl/chromedriver"  # ← 请修改为你自己的chromedriver路径
            service = Service(executable_path=chrome_driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(3)

            print("Chrome驱动初始化成功！")
            return True
        except Exception as e:
            print(f"Chrome驱动初始化失败: {e}")
            print("请确保已安装Chrome浏览器和ChromeDriver")
            return False

    def save_cookies(self):
        """保存cookies到文件"""
        try:
            cookies = self.driver.get_cookies()
            for cookie in cookies:
                if 'domain' not in cookie or 'taobao.com' not in cookie['domain']:
                    cookie['domain'] = '.taobao.com'

            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            print("Cookies已稳定保存")
        except Exception as e:
            print(f"保存cookies失败: {e}")

    def load_cookies(self):
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)

            self.driver.get("https://www.taobao.com")
            time.sleep(3)

            self.driver.delete_all_cookies()
            for cookie in cookies:
                if 'domain' in cookie and ('taobao.com' not in cookie['domain']):
                    cookie['domain'] = '.taobao.com'
                self.driver.add_cookie(cookie)

            self.driver.refresh()
            time.sleep(3)
            print("Cookies已加载，并重新刷新页面")
            return True
        except Exception as e:
            print(f"加载cookies失败: {e}")
            return False

    def login_with_qr(self):
        """使用二维码登录"""
        try:
            print("正在打开天猫登录页面...")
            self.driver.get("https://login.tmall.com/")
            time.sleep(3)

            # 查找二维码元素
            try:
                qr_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#J_QRCodeLogin img"))
                )
                print("二维码已显示，请使用手机淘宝扫描二维码登录")

                # 等待登录成功（检查是否跳转到首页或出现用户信息）
                login_success = False
                max_wait_time = 120  # 最多等待2分钟
                start_time = time.time()

                while time.time() - start_time < max_wait_time:
                    current_url = self.driver.current_url
                    if "login" not in current_url.lower() or self.check_login_status():
                        login_success = True
                        break
                    time.sleep(1)

                if login_success:
                    print("登录成功！")
                    self.save_cookies()
                    return True
                else:
                    print("登录超时，请重试")
                    return False

            except TimeoutException:
                print("⚠️ 未找到二维码，可能页面结构已变化")
                print("请手动登录天猫账号，登录完成后输入 '1' 确认继续...")
                while True:
                    confirm = input("👉 登录成功后请输入 1 确认继续：")
                    if confirm.strip() == "1":
                        break
                if self.check_login_status():
                    print("✅ 登录成功")
                    self.save_cookies()
                    return True
                else:
                    print("❌ 登录失败，请检查是否正确登录")
                    return False

        except Exception as e:
            print(f"登录过程中出错: {e}")
            return False

    def check_login_status(self):
        """检查登录状态"""
        try:
            # 检查 URL 是否不再是登录页
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                return True

            # 或者检查是否出现用户头像或昵称区域
            user_selectors = [
                ".site-nav-user", ".user-avatar", "#J_SiteNavLogin .nickname",
                ".site-nav-login-info", "#J_SiteNavLogin .s-user-name"
            ]

            for selector in user_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and elements[0].is_displayed():
                        return True
                except:
                    continue

            return False
        except Exception as e:
            print(f"登录状态判断出错: {e}")
            return False

    def search_products(self, keyword, max_pages=30):
        """搜索商品"""
        try:
            print(f"开始搜索商品: {keyword}")

            search_url = f"https://s.taobao.com/search?tab=mall&q={urllib.parse.quote(keyword)}"
            self.driver.get(search_url)
            time.sleep(5)  # 增加初始等待，确保页面加载完整

            # 页面加载后，尝试向下滚动触发懒加载
            for _ in range(5):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1)

            products = []

            for page in range(1, max_pages + 1):
                print(f"[调试] 当前爬取页码: {page}")
                print(f"正在爬取第 {page} 页...")
                page_start_time = time.time()

                # 明确使用XPath等待商品列表加载
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="content_items_wrapper"]/div'))
                    )
                except TimeoutException:
                    print("商品列表加载超时")
                    self.driver.save_screenshot("debug_page_timeout.png")
                    break

                page_products = self.parse_products_page(keyword)
                if page_products:
                    self.save_to_database(page_products)  # 每页保存一次
                products.extend(page_products)

                self.driver.save_screenshot(f"./debug_img/page_{page}.png")

                # 翻页操作
                if page < max_pages:
                    if not self.go_to_next_page():
                        print("没有更多页面了")
                        break

                page_end_time = time.time()
                print(f"[调试] 第 {page} 页爬取耗时: {page_end_time - page_start_time:.2f} 秒")
                time.sleep(2)

            print(f"总共爬取到 {len(products)} 个商品")
            return products

        except Exception as e:
            print(f"搜索商品时出错: {e}")
            return []

    def parse_products_page(self, category):
        """解析当前页面的商品信息"""
        products = []

        try:
            # 调试信息
            print(f"[调试] 当前页面地址: {self.driver.current_url}")
            # print(f"[调试] 页面HTML预览（前500字符）: {self.driver.page_source[:500]}")

            # 直接使用XPath查找商品元素
            product_elements = self.driver.find_elements(By.XPATH, '//*[@id="content_items_wrapper"]/div')
            print(f"[调试] 找到商品数量: {len(product_elements)}")

            if not product_elements:
                print("[调试] 未找到商品容器，保存当前页面截图为 debug_page.png")
                self.driver.save_screenshot("debug_page.png")
                return products

            for element in product_elements:
                try:
                    product_info = self.extract_product_info(element, category)
                    if product_info:
                        products.append(product_info)
                except Exception as e:
                    print(f"解析单个商品时出错: {e}")
                    continue

        except Exception as e:
            print(f"解析页面时出错: {e}")

        return products

    def extract_product_info(self, element, category):
        # 新增item_id字段
        product_info = {
            'item_id': '',  # 新增
            'category': category,
            'name': '',
            'price': '',
            'image_url': '',
            'shop_name': '',
            'shop_rating': ''
        }

        try:
            # 获取item_id
            a_elements = element.find_elements(By.XPATH, './/a[contains(@id, "item_id_")]')
            if not a_elements:
                print("商品id未找到，直接跳过")
                return None
            item_id = a_elements[0].get_attribute("id")
            if not item_id:
                print("未找到商品item_id，跳过该商品")
                return None
            product_info['item_id'] = item_id
            # 新增跳过逻辑：若数据库中已存在该item_id且image_url字段不为空，则跳过该商品
            existing_product = self.session.query(Product).filter_by(item_id=item_id).first()
            if existing_product and existing_product.image_url:
                print(f"跳过商品 {item_id}，因已存在且image_url不为空")
                return None
            base_xpath = f'//*[@id="{item_id}"]'

            # 商品图片URL
            img_xpath_1 = base_xpath + '/div/div[1]/div[2]/img[1]'
            img_xpath_2 = base_xpath + '/div/div[1]/div[1]/img[1]'
            try:
                try:
                    img_element = self.driver.find_element(By.XPATH, img_xpath_1)
                except:
                    img_element = self.driver.find_element(By.XPATH, img_xpath_2)
                img_url = img_element.get_attribute('src') or img_element.get_attribute('data-ks-lazyload')
                if img_url and img_url.startswith("//"):
                    img_url = "https:" + img_url
                product_info['image_url'] = img_url
            except Exception as e:
                print(f"商品图片URL提取失败, 产品类别和路径为", category, img_xpath_1, img_xpath_2)

            # 商品名称
            name_xpath = base_xpath + '/div/div[1]/div[3]/div/span'
            try:
                name_element = self.driver.find_element(By.XPATH, name_xpath)
                product_info['name'] = name_element.text.strip()
            except Exception as e:
                print(f"商品名称提取失败:", name_xpath)

            # 商品价格
            price_xpath = base_xpath + '//div[contains(@class, "priceInt")]'
            try:
                price_element = self.driver.find_element(By.XPATH, price_xpath)
                product_info['price'] = price_element.text.strip()
            except Exception as e:
                print(f"商品价格提取失败:", price_xpath)

            # 店铺名称
            shop_xpath = base_xpath + '//span[contains(@class, "shopNameText")]'
            try:
                shop_element = self.driver.find_element(By.XPATH, shop_xpath)
                product_info['shop_name'] = shop_element.text.strip()
            except Exception as e:
                print(f"店铺名称提取失败:", shop_xpath)

            # 暂无评分字段，保留默认
            product_info['shop_rating'] = ''

            # 验证商品名称是否成功获取
            if product_info['name']:
                return product_info
            else:
                print("商品名称为空，跳过该商品")
                return None

        except Exception as e:
            print(f"解析商品信息时发生异常:")
            return None

    def download_image(self, image_url, product_name, existing_product=None):
        """下载商品图片，使用SHA1处理文件名"""
        import hashlib
        try:
            if existing_product and existing_product.image_url:
                return existing_product.local_image_path
            if not image_url:
                return None

            # 下载图片
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(image_url, headers=headers, timeout=10)

            if response.status_code == 200:
                # 使用SHA1处理文件名
                sha1_hash = hashlib.sha1(response.content).hexdigest()
                filename = f"{sha1_hash}.jpg"
                filepath = os.path.join(self.image_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                print(f"图片已下载: {filename}")
                return filepath
            else:
                print(f"下载图片失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            print(f"下载图片时出错: {e}")
            return None

    def save_to_database(self, products):
        """将商品信息保存到数据库，去重并更新"""
        from sqlalchemy.exc import IntegrityError
        import hashlib
        try:
            saved_count = 0
            for product in products:
                if not product:
                    continue

                # 检查数据库是否存在此item_id
                existing_product = self.session.query(Product).filter_by(item_id=product['item_id']).first()

                # 下载图片
                local_image_path = None
                if product.get('image_url'):
                    local_image_path = self.download_image(product['image_url'], product['name'], existing_product)

                if existing_product:
                    # 存在则更新
                    existing_product.name = product['name'][:500]
                    existing_product.price = product.get('price', '')[:100]
                    existing_product.image_url = product.get('image_url', '')
                    existing_product.local_image_path = local_image_path or existing_product.local_image_path
                    existing_product.shop_name = product.get('shop_name', '')[:200]
                    existing_product.shop_rating = product.get('shop_rating', '')[:50]
                    existing_product.category = product.get('category', '')[:100]
                    existing_product.crawled_at = datetime.now()
                else:
                    # 新增数据
                    db_product = Product(
                        item_id=product['item_id'],
                        name=product['name'][:500],
                        price=product.get('price', '')[:100],
                        image_url=product.get('image_url', ''),
                        local_image_path=local_image_path or '',
                        shop_name=product.get('shop_name', '')[:200],
                        shop_rating=product.get('shop_rating', '')[:50],
                        category=product.get('category', '')[:100]
                    )
                    self.session.add(db_product)

                saved_count += 1

            self.session.commit()
            print(f"成功处理 {saved_count} 个商品到数据库（含更新和新增）")

        except IntegrityError as e:
            self.session.rollback()
            print(f"数据库完整性错误: {e}")
        except Exception as e:
            self.session.rollback()
            print(f"保存到数据库时出错: {e}")

    def go_to_next_page(self):
        """翻到下一页"""
        try:
            # 精确定位“下一页”按钮
            next_button = self.driver.find_element(By.CSS_SELECTOR, 'button.next-pagination-item.next-next')

            if next_button and next_button.is_enabled():
                self.driver.execute_script("arguments[0].click();", next_button)
                time.sleep(5)  # 等待页面加载
                return True
            else:
                print("已到达最后一页或下一页按钮不可用")
                return False

        except Exception as e:
            print(f"翻页时出错: ")
            return False

    def crawl(self, keywords, max_pages_per_keyword=30, need_login=False):
        """主爬取方法"""
        try:
            # 初始化驱动
            if not self.init_driver():
                return

            # 加载已保存的cookies
            cookies_loaded = self.load_cookies()

            # 登录逻辑调整：如果需要登录
            if need_login:
                if not cookies_loaded:
                    print("Cookies加载失败，建议手动登录并保存新cookie")
                    if not self.login_with_qr():
                        print("登录失败，退出爬取")
                        return
                else:
                    print("✅ 已加载 cookies，跳过登录")

            # 开始爬取
            all_products = []

            for keyword in keywords:
                print(f"\n开始爬取关键词: {keyword}")
                products = self.search_products(keyword, max_pages_per_keyword)
                all_products.extend(products)

                # 保存到数据库
                if products:
                    self.save_to_database(products)

                # 关键词间隔
                time.sleep(2)

            print(f"\n爬取完成！总共获取 {len(all_products)} 个商品")

        except Exception as e:
            print(f"爬取过程中出错: {e}")
        finally:
            if self.driver:
                self.driver.quit()
            if self.session:
                self.session.close()


def main():
    db_config = {
        'host': 'localhost',
        'port': 33309,
        'user': 'root',
        'password': '123456',
        'database': 'shopping_spark'
    }

    crawler = TmallCrawler(db_config, image_dir="shopping_crawl/tmall_images")

    # 启动爬虫，只调用 crawl，need_login=True 以保证首次登录流程可触发
    # crawler.crawl(keywords=["手机", "空调", "洗衣机"], max_pages_per_keyword=2, need_login=True)
    crawler.crawl(keywords=["珠宝"], max_pages_per_keyword=10, need_login=True)


if __name__ == "__main__":
    main()
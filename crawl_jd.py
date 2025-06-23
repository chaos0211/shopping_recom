import requests
import json
import time
from fake_useragent import UserAgent


def get_jd_products(keyword, page=1):
    ua = UserAgent()
    from urllib.parse import quote

    headers = {
        'User-Agent': ua.random,
        'Referer': f'https://search.jd.com/Search?keyword={quote(keyword)}'
    }

    url = f'https://search.jd.com/s_new.php?keyword={keyword}&page={page * 2 - 1}&scrolling=y&log_id={time.time()}'

    response = requests.get(url, headers=headers)
    response.encoding = response.apparent_encoding

    if response.status_code != 200:
        print(f"Failed to fetch page {page}")
        return []

    html = response.text
    # 提取商品信息通过 JSON 块
    try:
        from lxml import etree
        tree = etree.HTML(html)
        products = []
        lis = tree.xpath('//div[@id="J_goodsList"]/ul/li')
        for li in lis:
            try:
                title = ''.join(li.xpath('.//div[@class="p-name p-name-type-2"]/a/em//text()')).strip()
                price = ''.join(li.xpath('.//div[@class="p-price"]/strong/i/text()')).strip()
                comment_count = ''.join(li.xpath('.//div[@class="p-commit"]/strong/a/text()')).strip()
                shop_name = ''.join(li.xpath('.//div[@class="p-shop"]//a/text()')).strip()
                products.append({
                    'title': title,
                    'price': price,
                    'brand': shop_name,
                    'comment_count': comment_count
                })
            except Exception:
                continue
        return products
    except Exception as e:
        print("Parsing failed:", e)
        return []


# 示例：抓取前3页“笔记本”信息
all_data = []
for i in range(1, 4):
    items = get_jd_products("笔记本", page=i)
    all_data.extend(items)
    time.sleep(1)

# 输出示例
for item in all_data[:5]:
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(item)
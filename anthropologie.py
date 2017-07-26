import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import hashlib
import time
import math
import re
connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'https://www.anthropologie.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}


def grap(ID, url, sub_cate, cate):
    product_id = 0

    sql = "SELECT * FROM products WHERE identifier ='%s' AND site_id='%d'"
    sql = sql.format(ID, 4)
    cursor.execute(sql)
    data = cursor.fetchall()
    print len(data)
    if len(data) == 0:
        link = requests.get(url)
        page = BeautifulSoup(link.content, 'html.parser')
        name = page.find(class_='c-product-meta__h1').find(attrs={'itemprop': 'name'}).string.strip()
        price = page.find(class_='c-product-meta__current-price').text.strip().replace('$', '')
        original_price = "0"
        try:
            original_price = page.find(class_='c-product-meta__original-price').text.strip().replace('$', '')
        except:
            original_price = "0"
        brand_id = 0
        try:
            brand = page.find('p', attrs={'itemprop': 'brand'}).find('a').text.strip()
            sql = "SELECT * FROM brands WHERE name ='%s'"
            cursor.execute(sql % brand)
            data = cursor.fetchall()

            if len(data) > 0:
                brand_id = data[0][0]
            else:
                brandSql = "INSERT INTO brands(name) VALUES ('%s')" % (brand)
                brand_id = excute_insert_query(brandSql)
            print  brand_id
        except:
            print(".......Brand is empty......")

        sql = "INSERT INTO products(identifier, title,category_id,sub_category_name, price, brand_id,site_id, details_url,original_price) VALUES " \
              "('%s', '%s', '%d', '%s', '%s','%d','%d','%s','%s')" % (
                  ID, re.escape(name), cate, re.escape(sub_cate), price, brand_id, 4, url,original_price)
        product_id = excute_insert_query(sql)
        print product_id
        colors = page.find(class_='o-list-swatches').find_all('li')
        for li in colors:
            attr_id = 0
            color = li.find('a')['title']
            sql = "select id from attributes where name ='color' and value = '%s'"
            cursor.execute(sql % color)
            data = cursor.fetchall()
            if len(data) > 0:
                attr_id = data[0][0]
            else:
                colorSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('color', color)
                attr_id = excute_insert_query(colorSql)
            sql = "insert into products_attributes (product_id,attr_id) VALUES ('%d','%d')" % (product_id, attr_id)
            excute_insert_query(sql)

        sizes = page.find(class_='c-product-sizes__select').find_all('option')
        for option in sizes:
            size = option['value']
            if size != "None":
                print size
                sql = "select id from attributes where name ='size' and value = '%s'"
                cursor.execute(sql % size)
                data = cursor.fetchall()
                if len(data) > 0:
                    attr_id = data[0][0]
                else:
                    colorSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('size', size)
                    attr_id = excute_insert_query(colorSql)
                sql = "insert into products_attributes (product_id,attr_id) VALUES ('%d','%d')" % (product_id, attr_id)
                excute_insert_query(sql)

        images = page.find_all(class_='o-slider__slide')
        for img_div in images:
            image = img_div.find('img')['src']
            image = image.replace('hei=150', 'hei=900')
            img_name_db = create_file_name(image + time.ctime(int(time.time()))) + '.jpeg'
            img_name = 'product_images/' + img_name_db
            try:
               with open(img_name, "wb") as f:
                    f.write(requests.get("https:" + image).content)
                    sql = "insert into product_image (path,product_id) VALUES ('%s','%d')" % (img_name, product_id)
                    excute_insert_query(sql)
            except:
                print "File Exception"
            finally:
                pass





def explore_top_menu():
    main_cates = ['/new-clothes', '/dresses', '/clothes-trend', '/skirts', '/intimates-sleepwear', '/petite-clothes',
                  '/tops', '/jumpsuits-rompers', '/bottoms-jeans', '/bottoms-pants', '/activewear', '/sale-clothing',
                  '/jackets-coats', '/kids', '/kitchen', '/new-home', '/freshly-cut-sale?cm_sp=TOPNAV-_-SALE-_-NAV-SLUG',
                  '/freshly-cut-sale','/sale-home','/sale-all']
    link = requests.get(base_url)
    page = BeautifulSoup(link.content, 'html.parser')
    nav_items = page.find(class_='c-main-navigation__ul').find_all('li')
    for item in nav_items:
        url = item.find('a').get('href')
        cate = get_cate(url)
        print url
        print cate

        if url in main_cates :
            explore_side_menu(url,cate)
        else:
            explore_list_page(url,cate)


def explore_side_menu(url, cate):
    link = requests.get(base_url + url)
    page = BeautifulSoup(link.content, 'html.parser')
    menu_items = page.find(class_='s-category-navigation').find('ul').find_all('li')
    print menu_items
    for item in menu_items:
        anchor = item.find('a')
        sub_cate = anchor.text
        products_page = BeautifulSoup(requests.get(base_url + anchor['href']).content, 'html.parser')
        result = int(products_page.find(class_='c-results-count').text.replace('results', ''))
        count = int(math.ceil(result / 96) + 1)
        print sub_cate
        for i in range(0, count):
            print base_url+anchor.get('href')+'?page='+ str(i+1)
            list_page = BeautifulSoup(requests.get(base_url+anchor.get('href')+'?page='+ str(i+1)).content,'html.parser')
            products = list_page.find_all(class_='c-product-tile')
            print  get_cate(url)
            print sub_cate
            for product in products:
                ID = product.find('meta', attrs={'itemprop': 'productID'}).get('content')
                product_anchor = product.find('a', class_='c-product-tile__image-link').get('href')
                prod_url = base_url + product_anchor
                grap(ID, prod_url, sub_cate,cate)


def explore_list_page(url, cate):
    try:
        link = requests.get(base_url + url)
        page = BeautifulSoup(link.content, 'html.parser')
        sub_cate = page.find('a', class_='o-secondary-navigation__a--current').text
        result = int(page.find(class_='c-results-count').text.replace('results', ''))
        count = int(math.ceil(result / 96) + 1)
        for i in range(0, count):
            print link + '?page=' + str(i + 1)
            list_page = BeautifulSoup(requests.get( link + '?page=' + str(i + 1)).content,'html.parser')
            products = list_page.find_all(class_='c-product-tile')
            print sub_cate
            for product in products:
                ID = product.find('meta', attrs={'itemprop': 'productID'}).get('content')
                product_anchor = product.find('a', class_='c-product-tile__image-link').get('href')
                prod_url = base_url + product_anchor
                grap(ID, prod_url, sub_cate, cate)
    except:
        print("::::::::::::::::::: " + url + " Not a product list page::::::::::::::::::::")
    finally:
        pass


def create_file_name(image):
    return hashlib.md5(image).hexdigest()


def excute_insert_query(sql):
    insert_id = 0
    try:
        cursor.execute(sql)
        connection.commit()
        insert_id = cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print e
        # break
    return insert_id


def get_cate(url):
    ser = ["/furniture", '/living-room-furniture', '/living-room-furniture', '/furniture-office', '/home-candles',
           '/bedding', '/bedding-duvets', '/bedding-quilts-coverlets', '/sale-home', '/sale-furniture',
           '/sale-room-wall-decor', '/kitchen-dinner-plates', '/kitchen', '/limited-time-tabletop', '/new-home',
           '/furniture-guide', '/dining-room-furniture', '/kitchen-mugs-teacups''/kitchen-bowls', '/kitchen-glassware',
           '/kitchen-cookware-baking-supplies', '/kitchen-dishtowels', '/kitchen', '/garden-outdoor',
           '/terrain-pop-up-shop', '/garden-pots-planters', '/garden-outdoor', '/bathroom', '/organizing-storage',
           '/hardware',
           '/hardware-knobs', '/hardware-hooks', '/hardware', '/room-wall-decor', '/wallpaper', '/mirrors',
           '/kitchen-mugs-teacups',
           '/kitchen - bowls', '/home-top-rated' '/decor-art',
           '/decorative-pillows', '/room-wall-decor', '/rugs', '/curtains', '/lighting', '/books-stationery', '/books',
           '/books-stationary-calendars-planners',
           '/books-stationary-journals', '/books-stationery', '/home-gifts', '/gifts-for-her',
           '/gifts-phone-cases-tech', '/gifts-keychains-travel-accessories', '/gifts-monogram', '/sale-bedding',
           '/sale-home',
           '/home-gifts','/all-sale-home'

           ]
    if url == '/kids':
        return 4
    elif url in ser:
        return 3
    else:
        return 1

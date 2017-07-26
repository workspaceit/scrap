import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import hashlib
import time
import re

connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'https://www.gilt.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
site_id = 1


def create_file_name(image):
    return hashlib.md5(image).hexdigest()


def execute_insert_query(sql):
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


def explore_top_menu():
    page = BeautifulSoup(requests.get(base_url).content, 'html.parser')
    menus = page.find_all(class_='store-tab')
    for menu in menus:
        name = menu.get('data-store-name')
        if name == 'women' or name == 'men' or name == 'kids' or name == 'home':
            submenus = menu.find(class_='store-menu').find(class_='nav-categories').find('ul', class_='menu-actions')
            submenus = submenus.find_all('li', class_='menu-action')
            for submenu in submenus:
                anchor = submenu.find('a', class_='action-link')
                sub_cate = anchor.string.strip()
                url = anchor.get('href')
                print ("----On Top------")
                explore_list_page(base_url+url,name,sub_cate)


def explore_list_page(url,categoryname,sucategory):
    page = BeautifulSoup(requests.get(url).content, 'html.parser')
    pagination = page.find('div',class_='pagination')
    total_count = int(pagination.find('span',class_='total').string)
    for i in range(0,total_count+1):

        list_url = url+'q.display=&q.rows=48&q.start='+str(i*48)
        print ("............. page : " +list_url + "....................")
        list_page = BeautifulSoup(requests.get(list_url).content, 'html.parser')
        products = list_page.find_all('article', class_='product')
        for product in products:
            identifier = product.get('data-gilt-look-id')
            anchor = product.find('div', class_='url').find('a', class_='product-link')
            p_url =  anchor.get('href')
            grep(p_url,categoryname,sucategory,identifier)



def grep(url,categoryname,sucategory,identifier):
    sql = "SELECT * FROM products WHERE identifier ='%s' AND site_id='%d'"
    sql = sql.format(identifier, site_id)
    cursor.execute(sql)
    data = cursor.fetchall()
    print len(data)
    if len(data) == 0:
        print (".......... Handeling Product :with :"+categoryname+ "subcate :"+sucategory +"................")
        cate_id = product_type[categoryname]
        subcate = sucategory
        page = BeautifulSoup(requests.get(url).content, 'html.parser')
        brand_id = 0
        try:
            brand = page.find('h2', class_='brand-name').find('a', class_='brand-name-text').text.strip()
            print brand
            sql = "SELECT * FROM brands WHERE name ='%s'"
            cursor.execute(sql % brand)
            data = cursor.fetchall()

            if len(data) > 0:
                brand_id = data[0][0]
            else:
                brandSql = "INSERT INTO brands(name) VALUES ('%s')" % (brand)
                brand_id = execute_insert_query(brandSql)
            print  brand_id
        except:
            print(".......Brand is empty......")
        title = page.find('h1', class_='product-name').text.strip()
        price = page.find('div', class_='product-price-sale-container').find('span',class_='product-price-sale').string.strip()
        price_str = ''
        for char in price:
            if char.isnumeric() or char == '.':
                price_str = price_str + char

        print price_str
        or_str = ''
        try:
            original_price = page.find('div', class_='product-price-msrp').string.strip()
            for char in original_price:
                if char.isnumeric() or char == '.':
                    or_str = or_str + char
        except:
            or_str = '0'
        print or_str

        sql = "INSERT INTO products(identifier, title,category_id,sub_category_name, price, brand_id,site_id, details_url,original_price) VALUES " \
              "('%s', '%s', '%d', '%s', '%s','%d','%d','%s','%s')" % (
                  identifier, re.escape(title), cate_id, re.escape(subcate), price_str, brand_id, site_id,url, or_str)
        product_id = execute_insert_query(sql)

        colors = page.find('div', class_='sku-attributes-swatches').find('ul', class_='sku-attribute-values').find_all(
            'li',
            class_='sku-attribute-value')
        for li in colors:
            color = li.get('data-value-name')
            sql = "select id from attributes where name ='color' and value = '%s'"
            cursor.execute(sql % color)
            data = cursor.fetchall()
            if len(data) > 0:
                attr_id = data[0][0]
            else:
                colorSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('color', color)
                attr_id = execute_insert_query(colorSql)
            sql = "insert into products_attributes (product_id,attr_id) VALUES ('%d','%d')" % (product_id, attr_id)
            execute_insert_query(sql)

        sizes = page.find('div', class_='sku-attributes-size').find('ul', class_='sku-attribute-values').find_all('li',class_='sku-attribute-value')
        for li in sizes:
            size = li.get('data-value-name')
            sql = "select id from attributes where name ='size' and value = '%s'"
            cursor.execute(sql % size)
            data = cursor.fetchall()
            if len(data) > 0:
                attr_id = data[0][0]
            else:
                colorSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('size', size)
                attr_id = execute_insert_query(colorSql)
            sql = "insert into products_attributes (product_id,attr_id) VALUES ('%d','%d')" % (product_id, attr_id)
            execute_insert_query(sql)

        images = page.find(class_='product-thumbnails-container').find('ul',class_='product-photo-thumbnails').find_all(
            'li', class_='thumbnail')
        for li in images:
            image = li.find('img').get('src')
            last = image.rfind('/')
            image = image[:last] + '/926x1234.jpg'
            img_name_db = create_file_name(image + time.ctime(int(time.time()))) + '.jpeg'
            img_name = 'product_images/' + img_name_db
            with open(img_name, "wb") as f:
                f.write(requests.get("https:" + image).content)
                sql = "insert into product_image (path,product_id) VALUES ('%s','%d')" % (img_name, product_id)
                execute_insert_query(sql)


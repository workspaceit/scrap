import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import hashlib
import time
import selenium.webdriver as webdriver
import contextlib

phantomjs = 'phantomjs'

connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'http://www.forever21.com/'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    # 'kids': 4
}


def explore_top_menu():
    link = requests.get(base_url)
    page = BeautifulSoup(link.content, 'html.parser')
    nav_items = page.find(class_='new_header_left').find_all('li')
    selected_items = product_type.keys()
    for item in nav_items:
        anchor = item.find('a')
        url = anchor.get('href')
        try:
            anchor_name = anchor.string.lower()
            if anchor_name in selected_items:
                print("====================="+anchor_name+"==================")
                follow_next_page(url,product_type[anchor_name])
        except :
            pass



def follow_next_page(url,category):
    link = requests.get(url)
    page = BeautifulSoup(link.content, 'html.parser')
    child_items = page.find(class_='child_wrapper').find_all(class_='grandchild_wrapper')
    for item in child_items:
        anchor_list = item.find_all('a')
        for anchor in anchor_list:
            url =anchor.get('href')
            try:
                subcategory = anchor.string.lower()
                print("---------------subcategory:"+subcategory+"-----------")
                go_to_product_list_page(url,category,subcategory)
            except:
                pass



def go_to_product_list_page(url,category,subcategory):
    # link = requests.get(url)

    try:
        with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
            driver.get(url)
            content = driver.page_source
            page = BeautifulSoup(content, 'html.parser')
            pagination = page.find(class_="pagination")
            page_numbers = pagination.find(class_='p_number')
            all_buttons = page_numbers.find_all('button')
            first_item = all_buttons[0]
            last_item = all_buttons[-1]
            from_page =int(first_item.string)
            to_page = int(last_item.string)
            go_to_pages(url,from_page,to_page,category,subcategory)

    except Exception as e:
        print(e)
        print("Connection refused by the server..")


def go_to_pages(url,from_page, to_page,category,subcategory):

    if "|" in url:
        url = url.split("|")[0]

    for page in range(from_page,to_page+1):
        generated_url = url+"#pagesize=120&pageno="+str(page)
        go_to_paginated_list_page(generated_url,category,subcategory)

def go_to_paginated_list_page(url,category,subcategory):
    try:
        with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
            driver.get(url)
            content = driver.page_source
            page = BeautifulSoup(content, 'html.parser')
            items = page.find(id='ProductList')

            print(url)
            print("*******************list******************")
            products = items.find_all(class_='product_item')
            for product in products:
                product_name =product.get('data-name')
                product_identifier =product.get('data-sku')
                product_brand =product.get('data-brand')
                product_price =product.get('data-price')
                product_price_original = product.get('data-retail')
                if product_price == product_price_original:
                    product_price_original = 0

                url = product.find('a').get('href')
                go_to_product_detail_page(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory)

    except Exception as e:
        print(e)
        print("Connection refused by the server..")

def go_to_product_detail_page(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory):

    print("~~~~~~~~~~~~~~~producturl:"+url+"~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    link = requests.get(url)
    page = BeautifulSoup(link.content, 'html.parser')

    #colors

    item_color = page.find(class_="item_color")
    color_list = item_color.find_all('img')
    colors =[]
    for color in color_list:
        colors.append(color.get('alt'))

    # sizes

    item_size = page.find(class_="item_size")
    size_list = item_size.find_all('label')
    sizes = []
    for size in size_list:
        sizes.append(size.string)

    # images
    item_images = page.find(class_="pdp_thumbnail")
    image_list = item_images.find_all('img')
    images = []
    for image in image_list:
        src = image.get('src')
        src = src.replace("_58","_750")
        images.append(src)

    save_product_to_db(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory,colors,sizes,images)

def save_product_to_db(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory,colors,sizes,images):
    print("!!!!!!!!!!!!!!!!!!!!!!!!!SAVING INTO DATABASE !!!!!!!!!!!!!!!")

    if not is_product_exists(product_identifier,8):
       brand_id = get_brand_or_create(product_brand)
       product_id = save_product(product_identifier,product_name,category,subcategory,product_price,product_price_original,brand_id,8,url)

       for color in colors:
           color_id = get_color_or_create(color)
           save_product_attribute(product_id,color_id)

       for size in sizes:
           size_id = get_size_or_create(size)
           save_product_attribute(product_id, size_id)

       save_product_images(images,product_id)
    else:
        print("ALREADY SAVED IN DATABASE")



def is_product_exists(product_id,site_id):
    sql = "SELECT * FROM products WHERE identifier ={0} and site_id={1}"
    sql = sql.format(product_id,site_id)
    cursor.execute(sql)
    data = cursor.fetchall()
    if len(data)==0:
        return False
    else:
        return True

def get_brand_or_create(brand):
    sql = "SELECT * FROM brands WHERE name ='%s'"
    cursor.execute(sql % brand)
    data = cursor.fetchall()

    if len(data) > 0:
        brand_id = data[0][0]
    else:
        brandSql = "INSERT INTO brands(name) VALUES ('%s')" % (brand)
        brand_id = excute_insert_query(brandSql)

    return brand_id

def get_color_or_create(color):
    sql = "select id from attributes where name ='color' and value = '%s'"
    cursor.execute(sql % color)
    data = cursor.fetchall()
    if len(data) > 0:
        attr_id = data[0][0]
    else:
        colorSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('color', color)
        attr_id = excute_insert_query(colorSql)
    return attr_id

def get_size_or_create(size):
    sql = "select id from attributes where name ='size' and value = '%s'"
    cursor.execute(sql % size)
    data = cursor.fetchall()
    if len(data) > 0:
        attr_id = data[0][0]
    else:
        sizeSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('size', size)
        attr_id = excute_insert_query(sizeSql)
    return attr_id

def save_product_attribute(product_id,attr_id):
    sql = "insert into products_attributes (product_id,attr_id) VALUES ('%d','%d')" % (product_id, attr_id)
    excute_insert_query(sql)
    return True

def save_product_images(images,product_id):
    for image in images:
        img_name_db = create_file_name(image + time.ctime(int(time.time()))) + '.jpeg'
        img_name = 'product_images/' + img_name_db
        with open(img_name, "wb") as f:
            f.write(requests.get(image).content)
            sql = "insert into product_image (path,product_id) VALUES ('%s','%d')" % (img_name, product_id)
            excute_insert_query(sql)

def save_product(ID,name,category,sub_category,price,product_price_original,brand_id,site_id,url):

    sql = "INSERT INTO products(identifier, title,category_id,sub_category_name, price,original_price, brand_id,site_id, details_url) VALUES " \
          "('%s', '%s', '%d', '%s', '%s','%s','%d','%d','%s')" % (
              ID, name, category, sub_category, price,product_price_original, brand_id, site_id, url)
    product_id = excute_insert_query(sql)

    return product_id

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

import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import re
import json
import hashlib
import time
import selenium.webdriver as webdriver
import contextlib

connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'https://www.jcrew.com/'
product_type = {
    'women': 1,
    'men': 2,
}
phantomjs = 'phantomjs'

def go_to_product_list_page(url,category,subcategory):
    print("link:" + url)

    try:
        product_list_page = requests.get(url)
        product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')

        pagination = product_list_page_soup.find(class_="category__pagination")
        if pagination:
           paginated = pagination.find(class_='dropdown').find_all('option')
           first_item = 1
           last_item = paginated[-1].get('value')
           from_page = int(first_item)
           to_page = int(last_item)
           print ("Paginate from "+str(from_page)+" to "+str(to_page))
           go_to_pages(url,from_page,to_page,category,subcategory)
        else:
            go_to_paginated_list_page(url, category, subcategory)


    except:
        print("Connection refused by the server..")
        pass

def go_to_pages(url,from_page, to_page,category,subcategory):
    for page in range(from_page,to_page+1):
        regenerated_url = url+"?Nloc=en&Npge="+str(page)+"&Nrpp=60"
        go_to_paginated_list_page(regenerated_url,category,subcategory)

def go_to_paginated_list_page(url,category,subcategory):
    try:
        print url
        import dryscrape
        sess = dryscrape.Session()
        sess.visit(url)
        response = sess.body()
        # product_list_page = requests.get(url)
        product_list_page_soup = BeautifulSoup(response, 'html.parser')
        products = product_list_page_soup.find_all(class_='c-product-tile')

        for product in products:
            id = product.find(class_='js-product-tile').get('data-product')
            product_id = json.loads(id)
            product_id = product_id['id']
            product_name = product.find(class_='tile__detail--name').string

            product_url = product.find(class_='product-tile__link').get('href')
            product_url= base_url[:-1]+product_url
            product_brand =0


            product_price_container = product.find(class_='tile__detail--price--list')
            product_price = 0
            if product_price_container:
               product_price = product_price_container.string
               product_price = product_price.replace(",", "")
               product_price = re.findall("\d+\.\d+", product_price)
               product_price = product_price[0]


            product_price = str(product_price)
            product_original_price = str(0)

            go_to_product_detail_page(product_url,product_name,product_id,product_brand,product_price,product_original_price,category,subcategory)
    except Exception as e:
        pass

def go_to_product_detail_page(url,product_name,product_identifier,product_brand,product_price,product_original_price,category,subcategory):
    print  url
    import dryscrape
    sess = dryscrape.Session()
    sess.visit(url)
    response = sess.body()

    # product_dts_page  = requests.get(url)
    product_dts_soup = BeautifulSoup(response, 'html.parser')

    colors = []
    color_container = product_dts_soup.find(class_='colors-list')
    if color_container:
        color_list = color_container.find_all('li')
        for color in color_list:
            colors.append(color.get('data-name'))

    sizes = []
    size_container = product_dts_soup.find(class_='sizes-list')
    if size_container:
        size_list = size_container.find_all('li')
        for size in size_list:
            if 'is-unavailable' not in size.attrs['class']:
                sizes.append(size.get('data-name'))

    images = []
    image_container = product_dts_soup.find(class_='product__photos')
    if image_container:
        image_list = image_container.find_all('img')
        for image in image_list:
            images.append(image.get('src'))

    save_product_to_db(url, product_name, product_identifier, product_brand, product_price, product_original_price,category, subcategory, colors, sizes, images)

def save_product_to_db(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory,colors,sizes,images):
    print("!!!!!!!!!!!!!!!!!!!!!!!!!SAVING INTO DATABASE !!!!!!!!!!!!!!!")

    try:
        if not is_product_exists(product_identifier,15):
           if product_brand != 0:
               brand_id = get_brand_or_create(product_brand)
           else:
               brand_id = 0

           product_id = save_product(product_identifier,product_name,category,subcategory,product_price,product_price_original,brand_id,15,url)

           for color in colors:
               color_id = get_color_or_create(color)
               save_product_attribute(product_id,color_id)

           for size in sizes:
               size_id = get_size_or_create(size)
               save_product_attribute(product_id, size_id)

           save_product_images(images,product_id)
        else:
            print("ALREADY SAVED IN DATABASE")

    except Exception as e:
        print e

def is_product_exists(product_id,site_id):
    sql = "SELECT * FROM products WHERE identifier ='{0}' and site_id={1}"
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
    print images
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

def start_scrapper():

    import dryscrape
    sess = dryscrape.Session()
    sess.visit(base_url)
    response = sess.body()
    soup = BeautifulSoup(response,'html.parser')
    top = soup.find(class_='department-nav__list')
    menus = top.find_all('li',class_='department-nav__item')
    selected_items = product_type.keys()
    for menu in menus:
        anchor_item = menu
        anchor= anchor_item.get('data-department')
        if anchor in selected_items:
              categories = anchor_item.find_all('li',class_='nav-page__list-item')
              categories = categories[2:]
              for category in categories:
                   partial_link = category.find('a').get('href')
                   sub_category = category.find('a').find('span').string
                   link = base_url[:-1]+partial_link
                   if not link.endswith("?sidecar=true"):
                       go_to_product_list_page(link, product_type[anchor], sub_category)





start_scrapper()







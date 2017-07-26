import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import re
import json
import hashlib
import time
from selenium import webdriver
import contextlib
connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom1')
cursor = connection.cursor()
base_url = 'https://www.stylebop.com/'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
phantomjs = 'phantomjs'
site_id = 25

def go_to_product_list_page(url,category,subcategory):
    print("link:" + url)

    try:
        product_list_page = requests.get(url)
        product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
        pagination = product_list_page_soup.find(class_="pages")
        if pagination:
            first_item = 1
            last_item = pagination.find_all('a')[-2].getText()
            from_page = int(first_item)
            to_page = int(last_item)
            print ("Paginate from " + str(from_page) + " to " + str(to_page))
            go_to_pages(url, from_page, to_page, category, subcategory)
        else:
            go_to_paginated_list_page(url,category,subcategory)

    except:
        print("Connection refused by the server..")
        pass

def go_to_pages(url,from_page, to_page,category,subcategory):
    for page in range(from_page,to_page+1):
        if "?" in url:
            regenerated_url = url+"&p="+str(page)
        else:
            regenerated_url = url + "?p=" + str(page)
        go_to_paginated_list_page(regenerated_url,category,subcategory)

def go_to_paginated_list_page(url,category,subcategory):
    product_list_page = requests.get(url)
    product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
    product_container = product_list_page_soup.find(id='products-grid')
    products = product_container.find_all('li',class_='item')
    print url
    print len(products)
    for product in products:
        print "========="
        product_data = json.loads(product.get("data-product"))
        id= product_data["id"]
        product_url= product_data["url"]
        product_brand = product.find(class_="product-designer").getText().replace("'","")
        product_name = product.find(class_="product-name").find('a').get('title')
        price_container = product.find(class_="price-box")
        product_price = 0
        product_original_price = 0
        if price_container:
           special_price_container = product_container.find(class_="special-price")
           if special_price_container:
              product_price = special_price_container.find(class_='price').getText()

           old_price_container = product_container.find(class_="old-price")
           if old_price_container:
               product_original_price = old_price_container.find(class_='price').getText()

           rg_price_container = product_container.find(class_="reg-price")
           if rg_price_container:
               product_price = rg_price_container.find(class_='price').getText()

        product_price = product_price.strip()
        product_original_price = product_original_price.strip()

        product_price = re.findall("\d+\.\d+", product_price)
        product_price = product_price[0]

        product_original_price = re.findall("\d+\.\d+", product_original_price)
        product_original_price = product_original_price[0]

        go_to_product_detail_page(product_url,product_name,id,product_brand,category,subcategory,product_original_price, product_price)

def go_to_product_detail_page(url,product_name,product_identifier,product_brand,category,subcategory,product_original_price,product_price):

    product_dts_page  = requests.get(url)
    product_dts_soup = BeautifulSoup(product_dts_page.content, 'html.parser')



    size_container = product_dts_soup.find(class_='sizes')
    sizes=[]
    if size_container:
        sizeList = size_container.find_all('a')
        if sizeList:
            for size in sizeList:
                value = size.find('span').getText()
                if value:
                    sizes.append(value)
    else:
        size_container = product_dts_soup.find(class_='onesize')
        sizes.append(size_container.getText())



    color_container = product_dts_soup.find(class_='color-material')
    colors = []
    if color_container:
        colorText = color_container.getText()
        color = colorText.split(":")
        color = color[1].strip()
        colors.append(color)

    images=[]
    image_container = product_dts_soup.find(class_='product-image-gallery')
    if image_container:
        imageList = image_container.find_all('img')
        if imageList:
            for image in imageList:
                img = image.get('src')
                images.append(img)

    print url
    print colors
    print sizes
    print images
    # print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
    # print url
    # print colors
    # print images
    # print "<<<<<<<<<<<<<<<<<<<<<<<<<<<"
    save_product_to_db(url, product_name, product_identifier, product_brand, product_price, product_original_price,category, subcategory, colors, sizes, images)

def save_product_to_db(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory,colors,sizes,images):
    print("!!!!!!!!!!!!!!!!!!!!!!!!!SAVING INTO DATABASE !!!!!!!!!!!!!!!")

    if not is_product_exists(product_identifier,site_id):
       brand_id = get_brand_or_create(product_brand)
       product_id = save_product(product_identifier,product_name,category,subcategory,product_price,product_price_original,brand_id,site_id,url)

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
        if image.startswith("//"):
           image = "http:"+image


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
    try:
        page = requests.get(base_url)
        content = page.content
        soup = BeautifulSoup(content,"html.parser")
        store_switchs = soup.find(class_='store-switcher')
        store_list = store_switchs.find_all('a')
        for store in store_list:
            store_name = store.getText().lower()
            store_url = store.get('href')
            if store_name=="women":
                category =1
            elif store_name == "men":
                category = 2

            sale_page_url = store_url+"sale.html"
            sale_page = requests.get(sale_page_url)
            sale_soup = BeautifulSoup(sale_page.content,"html.parser")
            categories = sale_soup.find_all(class_="salecats")
            categories = categories[1:]
            for cat in categories:
                sub_cats = cat.find_all("a")
                for subcat in sub_cats:
                    sub_category = subcat.getText()

                    if not sub_category.startswith("ALL"):
                        url = subcat.get("href")
                        go_to_product_list_page(url,category,sub_category)

    except Exception as e:
        print e




start_scrapper()







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
base_url = 'http://www.lastcall.com/'
product_type = {
    'women': 1,
    'men': 2,
    # 'home': 3,
    # 'kids': 4
}
phantomjs = 'phantomjs'

def go_to_product_list_page(url,category,subcategory):
    # print("link:" + url)

    try:
        product_list_page = requests.get(url)
        product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
        pagination = product_list_page_soup.find(class_="pagination").find_all('li')
        first_item = 1
        last_item = pagination[-2].get('pagenum')
        from_page = int(first_item)
        to_page = int(last_item)
        # print ("Paginate from "+str(from_page)+" to "+str(to_page))
        go_to_pages(url,from_page,to_page,category,subcategory)

    except:
        print("Connection refused by the server..")
        pass

def go_to_pages(url,from_page, to_page,category,subcategory):

    for page in range(from_page,to_page+1):
        # print page
        regenerated_url = url+"#userConstrainedResults=true&refinements=&page="+str(page)+"&pageSize=30&sort=PCS_SORT&definitionPath=/nm/commerce/pagedef_rwd/template/EndecaDriven&onlineOnly=&updateFilter=false&allStoresInput=false&rwd=true&catalogId=cat6150001&selectedRecentSize=&activeFavoriteSizesCount=0&activeInteraction=true"
        go_to_paginated_list_page(regenerated_url,category,subcategory)

def go_to_paginated_list_page(url,category,subcategory):
    # print "Paginated :" +url
    product_list_page = requests.get(url)
    product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
    products = product_list_page_soup.find_all(class_='category-item')

    for product in products:
        product_id = product.get('id')
        if product_id:
            id = product.find(class_='quick-look').get('product_id')
            product_name = product.find(class_='productname').find('a').string
            product_brand = product.find(class_='productdesigner').find('a').string
            product_url = product.find(class_='productname').find('a').get('href')
            product_url = base_url+product_url[1:]
            product_name=product_name.replace("'","")
            subcategory=subcategory.replace("'","")
            go_to_product_detail_page(product_url,id, product_name,product_brand,category, subcategory)


def go_to_product_detail_page(url,product_identifier,product_name,product_brand,category,subcategory):

    print "----------"
    print url

    try:
        with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
            driver.get(url)
            content = driver.page_source
            product_dts_soup = BeautifulSoup(content, 'html.parser')

            price_container = product_dts_soup.find(class_='price-adornments-elim-suites')
            product_original_price =price_container.find(class_='item-price').string
            product_price = price_container.find(class_='sale-text').find(class_='item-price').string

            product_original_price=product_original_price.strip()[1:]
            product_price=product_price.strip()[1:]

            sizes = []
            size_container = product_dts_soup.find(class_='sizeSelectBox')
            if size_container:
                all_sizes = size_container.find_all('option')
                for size in all_sizes:
                    value =size.get('value')
                    if value:
                        sizes.append(value)

            colors = []
            color_container = product_dts_soup.find(class_='colorSelectBox')
            if color_container:
                all_colors = color_container.find_all('option')
                for color in all_colors:
                    value = color.get('value')
                    if value:
                        colors.append(value)


            images=[]
            image_container = product_dts_soup.find(class_='product-thumbnails')
            if image_container:
                print "MULTIPLE IMAGES:"
                imageList = image_container.find_all('li')
                for image in imageList:
                    img = image.find('img').get('data-zoom-url')
                    images.append(img)

            else:
                print "SINGLE IMAGE:"
                image_container = product_dts_soup.find(class_='main-img')
                img = image_container.find('img').get('data-zoom-url')
                images.append(img)

            save_product_to_db(url, product_name, product_identifier, product_brand, product_price, product_original_price,category, subcategory, colors, sizes, images)

    except Exception as e:
        print(e)
        print("Connection refused by the server..")





def save_product_to_db(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory,colors,sizes,images):
    print("!!!!!!!!!!!!!!!!!!!!!!!!!SAVING INTO DATABASE !!!!!!!!!!!!!!!")

    if not is_product_exists(product_identifier,17):
       brand_id = get_brand_or_create(product_brand)
       product_id = save_product(product_identifier,product_name,category,subcategory,product_price,product_price_original,brand_id,17,url)

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
    page = requests.get(base_url)
    soup = BeautifulSoup(page.content, 'html.parser')
    navs = soup.find_all(class_='silo-link')
    selected_items = product_type.keys()
    for nav in navs:
        anchor= nav.string.lower()
        if anchor in selected_items:
            parent_div = nav.parent
            silo_clms = parent_div.find_all(class_='silo-column')
            if anchor == 'men':
                silo_clms = silo_clms[:-2]
            else:
                silo_clms = silo_clms[:-1]

            for clm in silo_clms:
                hs = clm.find_all("h6")
                for h in hs:
                    link= h.find('a')
                    name = link.string
                    if name :
                        sub_category= name.strip()
                        list_page_link = link.get('href')
                        go_to_product_list_page(list_page_link, product_type[anchor], sub_category)





start_scrapper()







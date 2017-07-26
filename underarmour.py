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

connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'https://www.underarmour.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
phantomjs = 'phantomjs'
subcategories = [
    {
        "name": "Tops",
        "url": "/en-us/womens/tops/g/3cl?iid=dbo",
        "category":1
    },
    {
        "name": "Bottoms",
        "url": "/en-us/womens/bottoms/g/3co?iid=dbo",
        "category":1
    },
    {
        "name": "Footwear",
        "url": "/en-us/womens/footwear/g/3co?iid=dbo",
        "category":1
    },
    {
        "name": "Accessories",
        "url": "/en-us/womens/accessories/g/3co?iid=dbo",
        "category":1
    },
    {
        "name": "Under Armour Sportswear",
        "url": "/en-us/uas/womens/g/3c2vk?iid=dbo",
        "category":1
    },
    {
        "name": "All Womens",
        "url": "/en-us/womens/g/3c?iid=dbo",
        "category":1
    },
    {
        "name": "Tops",
        "url": "/en-us/mens/tops/g/39l?iid=dbo",
        "category":2
    },
    {
        "name": "Bottoms",
        "url": "/en-us/mens/bottoms/g/39o?iid=dbo",
        "category":2
    },
    {
        "name": "Footwear",
        "url": "/en-us/mens/footwear/g/39r?iid=dbo",
        "category":2
    },
    {
        "name": "Accessories",
        "url": "/en-us/mens/accessories/g/39u?iid=dbo",
        "category":2
    },
    {
        "name": "Under Armour Sportswear",
        "url": "/en-us/uas/mens/g/392vk?iid=dbo",
        "category":2
    },
    {
        "name": "All mens",
        "url": "/en-us/mens/g/39?iid=dbo",
        "category":2
    },



]
site_id= 23
def go_to_product_list_page(url,category,subcategory):
    print("link:" + url)

    try:
        driver = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true', '--ssl-protocol=TLSv1'])
        driver.get(url)
        html_source = driver.page_source
        product_dts_soup = BeautifulSoup(html_source, 'html.parser')
        products = product_dts_soup.find_all(class_='tile')
        intial_products= len(products)
        total = product_dts_soup.find(class_="product-count").find('span')
        total_products = int(total.getText())
        print "total " + str(total_products)
        no_of_scroll = total_products/intial_products
        print "No of scroll : "+str(no_of_scroll)
        html = ''
        if no_of_scroll > 1:
            for i in range(1, no_of_scroll+2):
                print i
                # driver.find_element_by_xpath("//*[@id='grid-container']/div/div[5]/div[2]/button").click()
                elements=driver.find_elements_by_xpath("//*[contains(text(), 'LOAD MORE')]")
                for elm in elements:
                    elm.click()
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(4)

            html = driver.page_source
        else:
            html = html_source
        get_all_product_list(html,category,subcategory)
    except Exception as e:
        print e

def get_all_product_list(html,category,subcategory):
    soup = BeautifulSoup(html,"html.parser")
    products = soup.find_all(class_='tile')
    print len(products)
    for product in products:
        id = product.get('data-pid')
        product_name = product.find(class_="title").getText()
        product_name = product_name.replace("'","")
        product_url = product.find("a").get("href")
        product_brand = "Under Armour"
        product_original_price = 0
        product_price = 0
        original_price_container = product.find("span",class_="price-orig")
        sale_price_container = product.find("span",class_="price-sale")
        price_container = product.find("span",class_="price")

        if original_price_container:
           product_original_price = original_price_container.getText()
           product_original_price = re.findall("\d+\.\d+", product_original_price)
           product_original_price = str(product_original_price[0])

        if sale_price_container:
            product_price = sale_price_container.getText()
            product_price = re.findall("\d+\.\d+", product_price)
            product_price = str(product_price[0])

        if product_original_price==product_price:
            product_original_price = 0

        if price_container:
            product_price = price_container.getText()
            product_price = re.findall("\d+\.\d+", product_price)
            product_price = str(product_price[0])

        go_to_product_detail_page(product_url,product_name,id,product_brand,category,subcategory,product_original_price,product_price)

def go_to_pages(url,from_page, to_page,category,subcategory):
    splited_url = url.split("?")
    first_part = splited_url[0]
    last_part = splited_url[1]
    for page in range(from_page,to_page+1):
        regenerated_url = first_part+"/Pageindex/"+str(page)+"?"+last_part
        go_to_paginated_list_page(regenerated_url,category,subcategory)

def go_to_paginated_list_page(url,category,subcategory):

    product_list_page = requests.get(url)
    product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
    products = product_list_page_soup.find_all(class_='productThumbnail')

    for product in products:
        id = product.get("id")
        product_url = product.find(class_='productThumbnailLink').get('href')
        product_brand = product.find(class_='brandName').find('a').string
        product_name = product.find(class_='prodName').find('a').string
        go_to_product_detail_page(product_url,product_name,id,product_brand,category,subcategory)

def go_to_product_detail_page(url,product_name,product_identifier,product_brand,category,subcategory,product_original_price,product_price):

    driver = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true', '--ssl-protocol=TLSv1'])
    driver.get(url)
    time.sleep(4)
    html_source = driver.page_source
    product_dts_soup = BeautifulSoup(html_source, 'html.parser')

    product_price=str(product_price)
    product_original_price=str(product_original_price)

    size_container = product_dts_soup.find(class_='buypanel_sizelist')
    sizes = []
    if size_container:
        sizeList = size_container.find_all('li')
        if sizeList:
            for size in sizeList:
                value = size.find('span').getText()
                if value:
                    sizes.append(value)


    color_container = product_dts_soup.find(class_='color-chip_list')
    colors = []
    if color_container:
        colorList = color_container.find_all('li')
        if colorList:
            for color in colorList:
                value = color.get('title')
                if value:
                    colors.append(value)

    images = []
    image_container = product_dts_soup.find(class_='zoom-area')

    if image_container:
        img = image_container.find('img')
        images.append(img.get('src'))

    print "----------------"
    print url
    print sizes
    print colors
    print images

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

# def start_scrapper():
#     try:
#         url ='https://www.underarmour.com/en-us/mens/tops/g/39l?iid=dbo'
#         driver = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true', '--ssl-protocol=TLSv1'])
#         driver.get(url)
#         for i in range(1, 22):
#             driver.find_element_by_xpath("//*[@id='grid-container']/div/div[5]/div[2]/button").click()
#             driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#             time.sleep(4)
#             html_source = driver.page_source
#             product_dts_soup = BeautifulSoup(html_source, 'html.parser')
#             products = product_dts_soup.find_all(class_='tile')
#             print "Product Length:"
#             print len(products)
#     except Exception as e:
#         print e


def start_scrapper():
    for subcategory in subcategories:
        url = base_url+subcategory["url"]
        go_to_product_list_page(url,subcategory["category"],subcategory["name"])

start_scrapper()







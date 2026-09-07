# Start by analyzing the given problem and understanding how it works.

# BE-1

    - Cause:
        System returned a 500 Internal Server Error status code.

        In file /BE/app/services/order.py 
        Line 69 executed meal = self.db.meals[first_line["mealId"]]
        The code tried to read key "mealId" which didn't match the Database Model using column name meal_id

    - Solution:
        Fixed in file /BE/app/services/order.py

        Before
            meal = self.db.meals[first_line["mealId"]]

        After
            meal = self.db.meals[first_line["meal_id"]]

# BE-2

    - Cause:
        
    - Solution:

# BE-3

    - Cause:

    - Solution:

# BE-4

    - Cause:

    - Solution:

# FE-1

    - Cause:

    - Solution:

# FE-2

    - Cause:

    - Solution:

### Test File
  - Framework: pytest + httpx AsyncClient (Integration Test)
  - Run: `python -m pytest {file_path} -v`

# BE-1 `test/be_1.py`
  - Test cases:
    1. `test_checkout_returns_201_with_order` — Successful checkout returns 201 status and the created order
    2. `test_cart_is_empty_after_checkout` — Cart is empty after checkout
    3. `test_stock_stays_the_same_after_checkout` — Inventory stock is not decremented twice
    4. `test_checkout_empty_cart_returns_400` — Checking out with an empty cart fails (400 Bad Request)
    5. `test_order_status_is_confirmed` — Order status is CONFIRMED
    6. `test_order_lines_match_cart_items` — Order line items match the items previously in the cart

------------------------------------------------------------------------

# เริ่มต้นจากการวิเคราะห์โจทที่ให้มาและทำความเข้าใจว่ามีการทำงานอย่างไร

# BE-1

    - สาเหตุ:
        ระบบส่งรหัสสถานะ 500 Internal Server Error 

        ในไฟล์ /BE/app/services/order.py 
        บรรทัดที่ 69 ได้มีการสั่ง meal = self.db.meals[first_line["mealId"]]
        โค้ดพยายามอ่าน key "mealId" ซึ่งไม่ตรงกับ Model ใน Database ที่ใช้ชื่อ field ว่า meal_id

    - วิธีการแก้ไข:
        เข้าไปแก้ที่ไฟล์ /BE/app/services/order.py

        จากเดิม
            meal = self.db.meals[first_line["mealId"]]

        เปลี่ยนเป็น 
            meal = self.db.meals[first_line["meal_id"]]

# BE-2

    - สาเหตุ:

    - วิธีการแก้ไข:

# BE-3

    - สาเหตุ:

    - วิธีการแก้ไข:

# BE-4

    - สาเหตุ:

    - วิธีการแก้ไข:

# FE-1

    - สาเหตุ:

    - วิธีการแก้ไข:

# FE-2

    - สาเหตุ:

    - วิธีการแก้ไข:

### File test
  - Framework: pytest + httpx AsyncClient (Integration Test)
  - Run: `python -m pytest {file_path} -v`

# BE-1 `test/be_1.py`
  - Test cases:
    1. `test_checkout_returns_201_with_order` — Checkout สำเร็จ ได้ status 201 + order กลับมา
    2. `test_cart_is_empty_after_checkout` — ตะกร้าว่างหลัง checkout
    3. `test_stock_stays_the_same_after_checkout` — Stock ไม่ถูก decrement ซ้ำ
    4. `test_checkout_empty_cart_returns_400` — ตะกร้าว่างไม่สามารถ checkout ได้ (400)
    5. `test_order_status_is_confirmed` — Order status = CONFIRMED
    6. `test_order_lines_match_cart_items` — Order lines ตรงกับสิ่งที่อยู่ใน cart

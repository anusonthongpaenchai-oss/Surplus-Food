# Start by analyzing the given problem and understanding how it works.

# BE-1

    - Bug: 
        System returned a 500 Internal Server Error status code.

    - Cause:
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

    - Bug:
        Cart displayed and charged customers using original_price instead of discounted_price.

    - Cause:

        In file /BE/app/services/cart.py
        Line 38 executed unit_price = meal.original_price
        The code assigned the full undiscounted price to unit_price, causing line_total and subtotal
        to be calculated at the wrong price. Because order.py builds OrderLine directly
        from get_cart() output, the inflated price was also committed to the order record.

    - Solution:
        Fixed in file /BE/app/services/cart.py

        Before
            unit_price = meal.original_price

        After
            unit_price = meal.discounted_price

# BE-3

    - Bug:
        Cancelling an order sets status to CANCELLED, but stock is not correctly restored.
        The stock restored was always a fixed value of 1, regardless of the actual order quantity.

    - Cause:
        In file /BE/app/services/order.py
        Line 107 had quantity=1 hardcoded in the stock.apply() call inside the cancel() method.
        This meant every cancellation always incremented stock by exactly 1,
        producing wrong results for any order with a different quantity.

    - Solution:
        Fixed in file /BE/app/services/order.py

        Before
            quantity=3

        After
            quantity=line.quantity


# BE-4

    - Bug:
        
    - Cause:

    - Solution:

# FE-1

    - Bug:
        
    - Cause:

    - Solution:

# FE-2

    - Bug:
        
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

# BE-2 `test/be_2.py`
  - Test cases:
    1. `test_cart_unit_price_uses_discounted_price` — Cart item unit_price equals discounted_price (fetched dynamically from GET /meals)
    2. `test_cart_line_total_uses_discounted_price` — Cart line_total = discounted_price × quantity (dynamic)
    3. `test_cart_subtotal_uses_discounted_price` — Cart subtotal = discounted_price × quantity (dynamic)
    4. `test_order_lines_use_discounted_price` — Order unit_price, line_total, and subtotal all inherit discounted prices from cart (dynamic)

# BE-3 `test/be_3.py`
  - Test cases:
    1. `test_stock_restored_to_initial_after_cancel` — Stock returns to initial value after cancellation (primary regression)
    2. `test_order_status_is_cancelled` — Order status equals CANCELLED after cancel
    3. `test_cancel_creates_increment_stock_event` — An INCREMENT stock event is recorded in the audit trail with correct quantity
    4. `test_multi_item_cancel_restores_all_meals_stock` — Cancelling a multi-item order restores stock for every meal line
    5. `test_cancel_already_cancelled_order_returns_400` — Double-cancel returns 400 and does not double-restore stock
    6. `test_cancel_nonexistent_order_returns_404` — Cancelling a non-existent order returns 404

------------------------------------------------------------------------

# เริ่มต้นจากการวิเคราะห์โจทที่ให้มาและทำความเข้าใจว่ามีการทำงานอย่างไร

# BE-1

    - Bug:
        ระบบส่งรหัสสถานะ 500 Internal Server Error 
    
    - สาเหตุ:

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

    - Bug:
        ตะกร้าสินค้าแสดงราคาและคิดเงินลูกค้าโดยใช้ original_price แทนที่จะเป็น discounted_price

    - สาเหตุ:

        ในไฟล์ /BE/app/services/cart.py
        บรรทัดที่ 38 ได้มีการสั่ง unit_price = meal.original_price
        โค้ดเลยนำราคาเต็มเดิมมากำหนดเป็น unit_price ทำให้ line_total และ subtotal
        คำนวณออกมาผิดพลาด และเนื่องจาก order.py นำข้อมูลจาก get_cart()
        มาสร้าง OrderLine โดยตรง ราคาที่ผิดจึงถูกบันทึกลงใน order ด้วย

    - วิธีการแก้ไข:
        เข้าไปแก้ที่ไฟล์ /BE/app/services/cart.py

        จากเดิม
            unit_price = meal.original_price

        เปลี่ยนเป็น
            unit_price = meal.discounted_price

# BE-3

    - Bug:
        การยกเลิก Order เปลี่ยนสถานะเป็น CANCELLED แต่ stock ที่คืนกลับมาไม่ถูกต้อง
        จำนวน stock ที่คืนถูก hardcode ไว้เป็น 1 เสมอ ไม่ว่า order จะมีจำนวนสินค้าเท่าไร

    - สาเหตุ:
        ในไฟล์ /BE/app/services/order.py
        บรรทัดที่ 107 มีการ hardcode quantity=1 ใน stock.apply() ภายใน cancel() method
        ทำให้ทุกการยกเลิก Order จะ increment stock ขึ้นมาแค่ 1 เสมอ
        ซึ่งให้ผลลัพธ์ที่ผิดสำหรับ order ที่มี quantity ต่างออกไป

    - วิธีการแก้ไข:
        เข้าไปแก้ที่ไฟล์ /BE/app/services/order.py

        จากเดิม
            quantity=1

        เปลี่ยนเป็น
            quantity=line.quantity


# BE-4

    - Bug:
        
    - สาเหตุ:

    - วิธีการแก้ไข:

# FE-1

    - Bug:
        
    - สาเหตุ:

    - วิธีการแก้ไข:

# FE-2

    - Bug:

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

# BE-2 `test/be_2.py`
  - Test cases:
    1. `test_cart_unit_price_uses_discounted_price` — unit_price ใน cart = discounted_price ที่ดึงจาก GET /meals โดยตรง
    2. `test_cart_line_total_uses_discounted_price` — line_total = discounted_price × quantity (ค่า dynamic)
    3. `test_cart_subtotal_uses_discounted_price` — subtotal = discounted_price × quantity (ค่า dynamic)
    4. `test_order_lines_use_discounted_price` — order unit_price, line_total, subtotal สืบทอดราคา discounted จาก cart (ค่า dynamic)

# BE-3 `test/be_3.py`
  - Test cases:
    1. `test_stock_restored_to_initial_after_cancel` — stock คืนกลับสู่ค่าเริ่มต้นหลัง cancel (primary regression)
    2. `test_order_status_is_cancelled` — order status = CANCELLED หลังยกเลิก
    3. `test_cancel_creates_increment_stock_event` — มี INCREMENT event บันทึกใน audit trail พร้อม quantity ที่ถูกต้อง
    4. `test_multi_item_cancel_restores_all_meals_stock` — cancel order หลาย item คืน stock ถูกทุก meal
    5. `test_cancel_already_cancelled_order_returns_400` — cancel ซ้ำต้อง error 400 และ stock ไม่เพิ่มขึ้นอีก
    6. `test_cancel_nonexistent_order_returns_404` — cancel order ที่ไม่มีอยู่ต้อง error 404

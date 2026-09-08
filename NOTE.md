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
        When increasing the item quantity in the cart, 
        the system did not deduct the additional delta stock, but instead increased the stock.

    - Cause:
        In file /BE/app/services/cart.py
        Line 101 had event_type=StockEventType.INCREMENT inside the update_item() method
        for the case when delta > 0 (quantity increased).
        This means every cart quantity increase was accidentally releasing stock
        rather than reserving it.

    - Solution:
        Fixed in file /BE/app/services/cart.py

        Before
            event_type=StockEventType.INCREMENT

        After
            event_type=StockEventType.DECREMENT

# FE-1

    - Bug:
        The Meals page displayed discounted_price as the "You pay" amount but was actually rendering original_price.
        Customers saw the full undiscounted price in the highlighted pay field instead of the reduced price.

    - Cause:
        In file /FE/src/pages/MealsPage.tsx
        Line 66 had formatBaht(meal.original_price) inside the <strong className="pay"> element.
        The original_price was being passed to the pay element, while it should have been reserved for the
        struck-through display only. Both fields were showing the same value.

    - Solution:
        Fixed in file /FE/src/pages/MealsPage.tsx

        Before
            <strong className="pay">{formatBaht(meal.original_price)}</strong>

        After
            <strong className="pay">{formatBaht(meal.discounted_price)}</strong>


# FE-2

    - Bug:
        Filtering by meal_id on the Stock Events page still returns every event.
        Typing a meal_id into the filter input and clicking "Apply filter" had no effect;
        the table always showed the full unfiltered list.

    - Cause:
        In file /FE/src/api/client.ts
        Line 118 built the query string as `?meal=<value>` instead of `?meal_id=<value>`.
        Because the endpoint declares the parameter as `meal_id`,
        the mismatched name caused FastAPI to treat the parameter as absent (None),
        so the service returned all events unconditionally.

    - Solution:
        Fixed in file /FE/src/api/client.ts

        Before
            const q = meal_id ? `?meal=${encodeURIComponent(meal_id)}` : "";

        After
            const q = meal_id ? `?meal_id=${encodeURIComponent(meal_id)}` : "";

### Test File
  - Framework: pytest + httpx AsyncClient (Integration Test)
  - Run: `python -m pytest {file_path} -v`

### Frontend Test File
  - Framework: Vitest + @testing-library/react + jsdom (Integration Test)
  - Run: `npx vitest run test/fe_1.ts` or `npm test`

# FE-1 `test/fe_1.ts`
  - Test cases:
    1. `test_pay_shows_discounted_price` — `.pay` element renders `discounted_price`, not `original_price`
    2. `test_strike_shows_original_price` — struck-through element renders `original_price`
    3. `test_pay_and_strike_never_equal` — pay price is always lower than struck-through price
    4. `test_multiple_meals_all_show_discounted_price` — every meal card uses `discounted_price` in `.pay`
    5. `test_out_of_stock_button_disabled` — "Add to cart" button is disabled when `stock_available < 1`

# FE-2 `test/fe_2.ts`
  - Test cases:
    1. `test_initial_load_fetches_all_events` — page loads without filter and shows all events
    2. `test_apply_filter_sends_meal_id_param` — clicking Apply filter sends `?meal_id=` (not the broken `?meal=`)
    3. `test_filtered_results_shown_in_table` — only matching `meal_id` rows are rendered after filter
    4. `test_clear_resets_filter_and_reloads` — clicking Clear resets input and reloads all events without filter param
    5. `test_empty_filter_does_not_send_param` — submitting empty input omits `meal_id` from query


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

# BE-4 `test/be_4.py`
  - Test cases:
    1. `test_increase_qty_decrements_stock_by_delta` — Increasing qty reserves only the delta, not the full new qty
    2. `test_increase_qty_creates_decrement_stock_event` — DECREMENT stock event recorded with correct delta quantity
    3. `test_decrease_qty_releases_stock_by_delta` — Decreasing qty releases the delta back to stock
    4. `test_same_qty_does_not_change_stock` — Updating to same qty triggers no stock change
    5. `test_update_nonexistent_cart_item_returns_404` — Updating an item not in cart returns 404

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
        เมื่อแก้ไขจำนวนสินค้าใน Cart เพิ่มขึ้น ระบบไม่ได้ไปตัดสต็อกส่วนต่างเพิ่ม แต่กลับไปเพิ่มสินค้าในสต็อกแทน

    - สาเหตุ:
        ในไฟล์ /BE/app/services/cart.py
        บรรทัดที่ 101 มีการใส่ event_type=StockEventType.INCREMENT ใน update_item()
        สำหรับกรณีที่ delta > 0 (จำนวนเพิ่มขึ้น)
        ทำให้ทุกครั้งที่เพิ่ม qty ใน cart กลับไป release stock แทนที่จะ reserve

    - วิธีการแก้ไข:
        เข้าไปแก้ที่ไฟล์ /BE/app/services/cart.py

        จากเดิม
            event_type=StockEventType.INCREMENT

        เปลี่ยนเป็น
            event_type=StockEventType.DECREMENT

# FE-1

    - Bug:
        หน้า Meals แสดงราคาในช่อง "You pay" ผิด โดยแสดง original_price แทนที่จะเป็น discounted_price
        ลูกค้าเห็นราคาเต็มที่ไม่มีส่วนลดในช่องราคาที่ต้องจ่าย แทนที่จะเห็นราคาลด

    - สาเหตุ:
        ในไฟล์ /FE/src/pages/MealsPage.tsx
        บรรทัดที่ 66 มีการใช้ formatBaht(meal.original_price) ภายใน <strong className="pay">
        ราคา original_price ถูกส่งไปแสดงในช่อง pay ทั้งที่ควรจะแสดงเฉพาะในช่องขีดฆ่าเท่านั้น
        ทำให้ทั้งสองช่องแสดงราคาเดียวกัน

    - วิธีการแก้ไข:
        เข้าไปแก้ที่ไฟล์ /FE/src/pages/MealsPage.tsx

        จากเดิม
            <strong className="pay">{formatBaht(meal.original_price)}</strong>

        เปลี่ยนเป็น
            <strong className="pay">{formatBaht(meal.discounted_price)}</strong>


# FE-2

    - Bug:
        การกรองข้อมูลด้วย meal_id ในหน้า Stock Events ยังคงแสดงผลทุก event อยู่
        แม้จะพิมพ์ meal_id ลงในช่อง filter แล้วกด "Apply filter" ก็ไม่มีผล
        ตารางยังแสดงข้อมูลทั้งหมดโดยไม่มีการกรอง

    - สาเหตุ:
        ในไฟล์ /FE/src/api/client.ts
        บรรทัดที่ 118 สร้าง query string เป็น `?meal=<value>` แทนที่จะเป็น `?meal_id=<value>`
        เนื่องจาก endpoint ประกาศ parameter ไว้ว่า meal_id
        ชื่อที่ไม่ตรงกันจึงทำให้ FastAPI มองว่าไม่มีการส่ง parameter มา (None)
        service จึงคืนข้อมูลทุก event โดยไม่มีการกรอง

    - วิธีการแก้ไข:
        เข้าไปแก้ที่ไฟล์ /FE/src/api/client.ts

        จากเดิม
            const q = meal_id ? `?meal=${encodeURIComponent(meal_id)}` : "";

        เปลี่ยนเป็น
            const q = meal_id ? `?meal_id=${encodeURIComponent(meal_id)}` : "";

### Backend File test 
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

# BE-4 `test/be_4.py`
  - Test cases:
    1. `test_increase_qty_decrements_stock_by_delta` — เพิ่ม qty ต้อง reserve stock เฉพาะส่วนต่าง (delta) เท่านั้น
    2. `test_increase_qty_creates_decrement_stock_event` — มี DECREMENT event บันทึกใน audit trail พร้อม delta ที่ถูกต้อง
    3. `test_decrease_qty_releases_stock_by_delta` — ลด qty ต้อง release stock คืนตามส่วนต่าง
    4. `test_same_qty_does_not_change_stock` — update qty เท่าเดิม ไม่มีการเปลี่ยนแปลง stock
    5. `test_update_nonexistent_cart_item_returns_404` — update item ที่ไม่มีใน cart ต้อง error 404

### Frontend File Test
  - Framework: Vitest + @testing-library/react + jsdom (Integration Test)
  - Run: `npx vitest run test/fe_1.ts` หรือ `npm test`

# FE-1 `test/fe_1.ts`
  - Test cases:
    1. `test_pay_shows_discounted_price` — element `.pay` แสดง `discounted_price` ไม่ใช่ `original_price`
    2. `test_strike_shows_original_price` — element ขีดฆ่าแสดง `original_price`
    3. `test_pay_and_strike_never_equal` — ราคา pay ต้องต่ำกว่าราคาขีดฆ่าเสมอ
    4. `test_multiple_meals_all_show_discounted_price` — ทุก meal card ใช้ `discounted_price` ใน `.pay`
    5. `test_out_of_stock_button_disabled` — ปุ่ม "Add to cart" ต้อง disabled เมื่อ `stock_available < 1`

# FE-2 `test/fe_2.ts`
  - Test cases:
    1. `test_initial_load_fetches_all_events` — โหลดหน้าแรกโดยไม่มี filter แสดงผลทุก event
    2. `test_apply_filter_sends_meal_id_param` — กด Apply filter ต้องส่ง `?meal_id=` (ไม่ใช่ `?meal=` ที่เคยผิด)
    3. `test_filtered_results_shown_in_table` — หลัง filter แสดงเฉพาะ row ที่ตรงกับ `meal_id`
    4. `test_clear_resets_filter_and_reloads` — กด Clear รีเซ็ต input และโหลดใหม่โดยไม่มี filter param
    5. `test_empty_filter_does_not_send_param` — กด Apply ตอน input ว่าง ต้องไม่ส่ง `meal_id` ใน query

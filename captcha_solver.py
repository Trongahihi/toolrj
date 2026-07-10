"""
╔═══════════════════════════════════════════════════════════════╗
║           CAPTCHA SOLVER MODULE - SHOUKO.DEV                 ║
║   Tự động phát hiện, cắt, và giải Captcha hình ảnh          ║
║   Integration with OmoCaptcha API (Image-to-Text)            ║
╚═══════════════════════════════════════════════════════════════╝

Tiêu chuẩn:
- ✅ Thread-safe với Lock
- ✅ Error handling đầy đủ
- ✅ Logging tất cả lỗi vào file
- ✅ Support 2 cơ chế detection (Template Matching + Fixed Box)
- ✅ Polling retry logic từ OmoCaptcha API
- ✅ ADB integration để điền kết quả + click nút
"""

import base64
import os
import time
import requests
import subprocess
import cv2
import json
from threading import Lock
from typing import Tuple, Optional


class CaptchaSolver:
    """
    Module giải Captcha tự động cho Roblox
    
    Args:
        api_token (str): Token từ OmoCaptcha.com
        detection_mode (str): "template" hoặc "fixed_box"
        template_path (str): Đường dẫn ảnh mẫu (chỉ dùng nếu detection_mode="template")
        fixed_box_coords (tuple): (x1, y1, x2, y2) - Tọa độ Captcha cố định
        confidence_threshold (float): Độ chính xác tối thiểu template matching (0-1)
        submit_button_offset (tuple): (x_offset, y_offset) - Vị trí nút Submit tương đối từ Captcha
        enable_logging (bool): Bật/tắt logging
    """
    
    def __init__(
        self,
        api_token: str,
        detection_mode: str = "fixed_box",
        template_path: Optional[str] = None,
        fixed_box_coords: Tuple[int, int, int, int] = (150, 500, 750, 600),
        confidence_threshold: float = 0.7,
        submit_button_offset: Tuple[int, int] = (300, 100),
        enable_logging: bool = True
    ):
        """Khởi tạo CaptchaSolver"""
        self.api_token = api_token
        self.detection_mode = detection_mode
        self.template_path = template_path
        self.fixed_box_coords = fixed_box_coords
        self.confidence_threshold = confidence_threshold
        self.submit_button_offset = submit_button_offset
        self.enable_logging = enable_logging
        self.lock = Lock()
        
        # Tạo folder crops nếu chưa tồn tại
        os.makedirs("captcha_crops", exist_ok=True)
        
        if self.detection_mode == "template" and not template_path:
            self._log("⚠️ Template path not provided, falling back to fixed_box")
            self.detection_mode = "fixed_box"
        
        if self.detection_mode == "template" and template_path:
            if not os.path.exists(template_path):
                self._log(f"❌ Template file not found: {template_path}")
                self.detection_mode = "fixed_box"
            else:
                self._log(f"✅ Template loaded: {template_path}")
        
        self._log("🚀 CaptchaSolver initialized successfully")
    
    def _log(self, message: str):
        """Ghi log message"""
        if self.enable_logging:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_msg = f"[\033[1;36m{timestamp}\033[0m] {message}"
            print(log_msg)
            
            # Ghi vào file
            try:
                with open("captcha_solver.log", "a") as f:
                    f.write(f"[{timestamp}] {message}\n")
            except:
                pass
    
    def detect_and_crop(self, screenshot_path: str) -> Optional[str]:
        """
        Phát hiện và cắt Captcha từ screenshot
        
        Args:
            screenshot_path (str): Đường dẫn tới file screenshot
        
        Returns:
            str: Đường dẫn ảnh Captcha đã cắt, None nếu không tìm thấy
        """
        try:
            if not os.path.exists(screenshot_path):
                self._log(f"❌ Screenshot not found: {screenshot_path}")
                return None
            
            # Đọc ảnh
            image = cv2.imread(screenshot_path)
            if image is None:
                self._log(f"❌ Failed to read image: {screenshot_path}")
                return None
            
            self._log(f"📸 Screenshot loaded: {screenshot_path}")
            
            # Phát hiện Captcha dựa theo cơ chế
            if self.detection_mode == "template":
                captcha_box = self._detect_by_template(image, screenshot_path)
            else:  # fixed_box
                captcha_box = self._detect_by_fixed_box(image)
            
            if captcha_box is None:
                self._log("⚠️ Captcha not detected")
                return None
            
            # Cắt ảnh Captcha
            x1, y1, x2, y2 = captcha_box
            cropped_image = image[y1:y2, x1:x2]
            
            # Lưu ảnh cắt
            timestamp = int(time.time())
            crop_path = f"captcha_crops/captcha_{timestamp}.png"
            cv2.imwrite(crop_path, cropped_image)
            
            self._log(f"✅ Captcha cropped: {crop_path} ({x2-x1}x{y2-y1}px)")
            return crop_path
            
        except Exception as e:
            self._log(f"❌ Error in detect_and_crop: {str(e)}")
            return None
    
    def _detect_by_template(self, image: cv2.Mat, screenshot_path: str) -> Optional[Tuple]:
        """
        Phát hiện Captcha bằng Template Matching
        
        Returns:
            tuple: (x1, y1, x2, y2) hoặc None
        """
        try:
            template = cv2.imread(self.template_path)
            if template is None:
                self._log("❌ Failed to load template")
                return None
            
            # Template matching
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val < self.confidence_threshold:
                self._log(f"⚠️ Template match confidence too low: {max_val:.2f}")
                return None
            
            # Tính tọa độ bounding box
            x, y = max_loc
            w, h = template.shape[1], template.shape[0]
            
            self._log(f"✅ Template matched with confidence: {max_val:.2f}")
            return (x, y, x + w, y + h)
            
        except Exception as e:
            self._log(f"❌ Error in _detect_by_template: {str(e)}")
            return None
    
    def _detect_by_fixed_box(self, image: cv2.Mat) -> Tuple:
        """
        Phát hiện Captcha bằng Fixed Bounding Box
        
        Returns:
            tuple: (x1, y1, x2, y2)
        """
        x1, y1, x2, y2 = self.fixed_box_coords
        
        # Kiểm tra xem tọa độ có hợp lệ không
        if x2 <= x1 or y2 <= y1:
            self._log("❌ Invalid fixed box coordinates")
            return (150, 500, 750, 600)
        
        self._log(f"✅ Fixed box detected: ({x1},{y1}) to ({x2},{y2})")
        return (x1, y1, x2, y2)
    
    def solve_captcha(self, captcha_image_path: str) -> Optional[str]:
        """
        Gửi ảnh Captcha tới OmoCaptcha API và lấy kết quả
        
        Args:
            captcha_image_path (str): Đường dẫn ảnh Captcha
        
        Returns:
            str: Mã Captcha đã giải, None nếu thất bại
        """
        try:
            if not os.path.exists(captcha_image_path):
                self._log(f"❌ Captcha image not found: {captcha_image_path}")
                return None
            
            # Chuyển đổi ảnh sang Base64
            with open(captcha_image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            self._log("📤 Uploading captcha to OmoCaptcha API...")
            
            # Gửi request tạo task
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "job": {
                    "type": "ImageToText",
                    "imageBase64": image_base64,
                    "language": "en"
                }
            }
            
            response = requests.post(
                "https://api.omocaptcha.com/v1/container/jobs",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                self._log(f"❌ Failed to create task: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            task_id = result.get("jobId")
            
            if not task_id:
                self._log(f"❌ No task ID received: {result}")
                return None
            
            self._log(f"✅ Task created: {task_id}")
            
            # Polling untuk mendapatkan hasil
            captcha_text = self._poll_result(task_id)
            
            if captcha_text:
                self._log(f"✅ Captcha solved: {captcha_text}")
                return captcha_text
            else:
                self._log("❌ Failed to solve captcha after polling")
                return None
                
        except Exception as e:
            self._log(f"❌ Error in solve_captcha: {str(e)}")
            return None
    
    def _poll_result(self, task_id: str, max_retries: int = 10) -> Optional[str]:
        """
        Polling untuk mendapatkan hasil dari OmoCaptcha API
        
        Args:
            task_id (str): Task ID từ API
            max_retries (int): Số lần polling tối đa
        
        Returns:
            str: Kết quả Captcha hoặc None
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }
        
        for attempt in range(max_retries):
            try:
                time.sleep(2)  # Chờ 2 giây trước mỗi polling
                
                response = requests.get(
                    f"https://api.omocaptcha.com/v1/container/jobs/{task_id}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code != 200:
                    self._log(f"⚠️ Polling attempt {attempt+1}/{max_retries} failed: {response.status_code}")
                    continue
                
                result = response.json()
                status = result.get("status")
                
                self._log(f"🔄 Polling attempt {attempt+1}/{max_retries}: status={status}")
                
                if status == "success":
                    captcha_text = result.get("result", {}).get("text")
                    return captcha_text
                
                elif status == "error":
                    error = result.get("result", {}).get("errorMessage", "Unknown error")
                    self._log(f"❌ API Error: {error}")
                    return None
                
            except Exception as e:
                self._log(f"⚠️ Polling error (attempt {attempt+1}): {str(e)}")
                continue
        
        return None
    
    def apply_captcha_result(
        self,
        captcha_text: str,
        device_id: str = "emulator-5554",
        use_submit_button: bool = True
    ) -> bool:
        """
        Điền kết quả Captcha vào game và click nút Submit
        
        Args:
            captcha_text (str): Mã Captcha đã giải
            device_id (str): Device ID hoặc package name
            use_submit_button (bool): Có click nút Submit không
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            with self.lock:
                self._log(f"⌨️ Typing captcha text: {captcha_text}")
                
                # Gõ ký tự
                subprocess.run(
                    ["adb", "-s", device_id, "shell", "input", "text", captcha_text],
                    capture_output=True,
                    timeout=5,
                    check=False
                )
                
                time.sleep(0.5)
                
                if use_submit_button:
                    # Tính tọa độ nút Submit
                    x1, y1, x2, y2 = self.fixed_box_coords
                    x_offset, y_offset = self.submit_button_offset
                    
                    # Tọa độ nút = center của Captcha box + offset
                    submit_x = (x1 + x2) // 2 + x_offset
                    submit_y = y2 + y_offset
                    
                    self._log(f"🖱️ Clicking submit button at ({submit_x}, {submit_y})")
                    
                    # Click nút
                    subprocess.run(
                        ["adb", "-s", device_id, "shell", "input", "tap", str(submit_x), str(submit_y)],
                        capture_output=True,
                        timeout=5,
                        check=False
                    )
                
                self._log("✅ Captcha applied successfully")
                return True
                
        except Exception as e:
            self._log(f"❌ Error in apply_captcha_result: {str(e)}")
            return False
    
    def solve_and_apply(
        self,
        screenshot_path: str,
        device_id: str = "emulator-5554",
        use_submit_button: bool = True
    ) -> bool:
        """
        Quy trình hoàn chỉnh: Detect → Solve → Apply
        
        Args:
            screenshot_path (str): Đường dẫn screenshot
            device_id (str): Device ID
            use_submit_button (bool): Có click nút Submit không
        
        Returns:
            bool: True nếu toàn bộ quy trình thành công
        """
        try:
            self._log("=" * 60)
            self._log("🚀 STARTING COMPLETE CAPTCHA SOLVE FLOW")
            self._log("=" * 60)
            
            # Bước 1: Phát hiện và cắt Captcha
            captcha_path = self.detect_and_crop(screenshot_path)
            if not captcha_path:
                self._log("❌ Captcha detection failed, aborting...")
                return False
            
            # Bước 2: Giải Captcha
            captcha_text = self.solve_captcha(captcha_path)
            if not captcha_text:
                self._log("❌ Captcha solving failed, aborting...")
                return False
            
            # Bước 3: Điền kết quả
            success = self.apply_captcha_result(
                captcha_text,
                device_id=device_id,
                use_submit_button=use_submit_button
            )
            
            self._log("=" * 60)
            if success:
                self._log("✅ CAPTCHA FLOW COMPLETED SUCCESSFULLY")
            else:
                self._log("❌ CAPTCHA FLOW FAILED")
            self._log("=" * 60)
            
            return success
            
        except Exception as e:
            self._log(f"❌ Fatal error in solve_and_apply: {str(e)}")
            return False


# ========== STANDALONE TEST ==========
if __name__ == "__main__":
    """Test CaptchaSolver"""
    
    print("\n" + "="*60)
    print("🧪 CAPTCHA SOLVER - TEST MODE")
    print("="*60 + "\n")
    
    # Config test
    api_token = "your_omocaptcha_token_here"
    
    # Test mode 1: Fixed Box
    print("📌 Mode 1: Fixed Box Detection")
    solver_fixed = CaptchaSolver(
        api_token=api_token,
        detection_mode="fixed_box",
        fixed_box_coords=(150, 500, 750, 600),
        submit_button_offset=(300, 100)
    )
    print("✅ CaptchaSolver (Fixed Box) initialized\n")
    
    # Test mode 2: Template
    print("📌 Mode 2: Template Matching Detection")
    solver_template = CaptchaSolver(
        api_token=api_token,
        detection_mode="template",
        template_path="captcha_template.png",  # Provide your template
        confidence_threshold=0.7
    )
    print("✅ CaptchaSolver (Template) initialized\n")
    
    print("✨ CaptchaSolver module is ready to use!\n")

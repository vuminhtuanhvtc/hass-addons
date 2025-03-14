import config
import requests
import cv2
import numpy as np
import urllib
import time
import json
import gesturemodelfunctions
import gc
import contextlib

def pubinitial(cameraname):
    topic = config.config['gesture']['topic'] + "/" + cameraname
    payload = {'person': '', 'gesture': ''}
    print("Publishing initial state for: " + cameraname)
    ret = config.client.publish(topic, json.dumps(payload), retain=True)
    config.sentpayload[cameraname] = payload

def pubresults(cameraname, name, gesture):
    topic = config.config['gesture']['topic'] + "/" + cameraname
    payload = {'person': name, 'gesture': gesture}
    if config.sentpayload[cameraname] != payload:
        print("publishing to " + topic)
        print("Payload: " + str(payload))
        ret = config.client.publish(topic, json.dumps(payload), retain=True)
        config.sentpayload[cameraname] = payload

def getmatches(cameraname):
    # do face recognition on the latest image from frigate
    url = "http://" + config.config['double-take']['host'] + ":" + \
          str(config.config['double-take']['port']) + \
          "/api/recognize?url=http://" + config.config['frigate']['host'] + ":" + \
          str(config.config['frigate']['port']) + "/api/" + cameraname + \
          "/latest.jpg&attempts=1&camera=" + cameraname
    response = requests.get(url)
    output = response.json()
    response.close()
    return output

def getlatestimg(cameraname):
    url = "http://" + config.config['frigate']['host'] + ":" + str(config.config['frigate']['port']) + \
          "/api/" + cameraname + "/latest.jpg"
    with contextlib.closing(urllib.request.urlopen(url)) as req:
        arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
    img = cv2.imdecode(arr, -1)
    return img

def is_person_allowed(person_name):
    """Kiểm tra xem người này có được phép xử lý không dựa trên cấu hình"""
    allowed_persons = config.config['gesture'].get('allowed_persons', [])
    # Nếu danh sách trống, cho phép tất cả
    if not allowed_persons:
        return True
    # Nếu có danh sách, kiểm tra xem người này có trong danh sách không
    return person_name in allowed_persons

def should_process_result(matches):
    """Kiểm tra xem kết quả này có nên được xử lý không dựa trên cấu hình"""
    # Nếu cấu hình detect_all_results là True, sẽ xử lý khi có bất kỳ kết quả nào
    detect_all_results = config.config['gesture'].get('detect_all_results', False)
    
    # Xử lý khi có match
    if int(matches['counts']['match']) > 0:
        return True
    
    # Nếu detect_all_results=True, xử lý khi có bất kỳ kết quả nào khác 0
    if detect_all_results:
        if (int(matches['counts']['person']) > 0 or 
            int(matches['counts']['miss']) > 0 or 
            int(matches['counts']['unknown']) > 0):
            return True
    
    return False

def get_person_to_process(matches):
    """Tìm người phù hợp nhất để xử lý từ kết quả nhận diện"""
    # Ưu tiên các match trước
    if int(matches['counts']['match']) > 0:
        # Tìm match lớn nhất
        biggestmatchsize = 0
        biggestmatch = None
        
        for match in matches['matches']:
            if not is_person_allowed(match['name']):
                continue
                
            matchsize = match['box']['width'] * match['box']['height']
            if matchsize > biggestmatchsize:
                biggestmatchsize = matchsize
                biggestmatch = match
        
        if biggestmatch:
            return biggestmatch['name'], biggestmatch['box']
    
    # Nếu không có match hoặc không có match được phép, xử lý miss và unknown
    detect_all_results = config.config['gesture'].get('detect_all_results', False)
    if detect_all_results:
        # Xử lý miss
        if int(matches['counts']['miss']) > 0:
            for miss in matches['misses']:
                if not is_person_allowed(miss['name']):
                    continue
                return miss['name'], miss['box']
        
        # Xử lý unknown
        if int(matches['counts']['unknown']) > 0:
            # Chọn unknown lớn nhất
            biggestunknownsize = 0
            biggestunknown = None
            
            for unknown in matches['unknowns']:
                unknownsize = unknown['box']['width'] * unknown['box']['height']
                if unknownsize > biggestunknownsize:
                    biggestunknownsize = unknownsize
                    biggestunknown = unknown
            
            if biggestunknown:
                return "unknown", biggestunknown['box']
    
    return None, None

def lookforhands():
    # publish to the availablility topic with retain turned on
    # HA seems to need this to keep the sensor from going "unavailable"
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Publishing availability")
    topic = config.config['gesture']['topic'] + "/" + 'availability'
    payload = "online"
    ret = config.client.publish(topic, payload, retain=True)
    topic = config.config['gesture']['topic'] + "/" + 'availability2'
    payload = "online"
    ret = config.client.publish(topic, payload, retain=True)
    
    # publish payload with no name or gestures for each camera
    for camera in config.config['frigate']['cameras']:
        pubinitial(camera)
    
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Starting main loop - checking for gestures")
    
    # Lưu trạng thái camera trước đó để tránh log lặp lại
    previous_camera_states = {}
    for cameraname in config.numpersons:
        previous_camera_states[cameraname] = -1  # Khởi tạo với giá trị không tồn tại
    
    while(True):
        for cameraname in config.numpersons:
            numcamerapeople = config.numpersons[cameraname]
            topic = config.config['gesture']['topic'] + "/" + cameraname
            
            # Chỉ in log khi số người thay đổi
            if previous_camera_states[cameraname] != numcamerapeople:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: {numcamerapeople} người")
                previous_camera_states[cameraname] = numcamerapeople
            
            # if there are people in front a camera
            if numcamerapeople > 0:
                process_start_time = time.time()
                try:
                    # Kiểm tra xem cần xử lý trực tiếp hay qua double-take
                    use_doubletake = False
                    
                    # Kiểm tra xem có cấu hình double-take không
                    if 'double-take' in config.config:
                        # Nếu không có danh sách camera, xử lý tất cả qua double-take
                        if 'camera' not in config.config['double-take']:
                            use_doubletake = True
                        # Nếu có danh sách camera, kiểm tra xem camera hiện tại có trong danh sách không
                        elif cameraname in config.config['double-take']['camera']:
                            use_doubletake = True
                    
                    if use_doubletake:
                        # Xử lý qua double-take
                        dt_start_time = time.time()
                        matches = getmatches(cameraname)
                        dt_time = time.time() - dt_start_time
                        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: Double-Take processed in {dt_time:.3f}s")
                        
                        # Kiểm tra xem có nên xử lý kết quả này không
                        should_process = should_process_result(matches)
                        
                        if should_process:
                            # Tìm người phù hợp để xử lý
                            person_name, person_box = get_person_to_process(matches)
                            
                            if person_name:
                                # Lấy hình ảnh và phân tích cử chỉ
                                img_start_time = time.time()
                                img = getlatestimg(cameraname)
                                img_time = time.time() - img_start_time
                                
                                gesture_start_time = time.time()
                                gesture = gesturemodelfunctions.gesturemodelmatch(img)
                                gesture_time = time.time() - gesture_start_time
                                
                                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: Gesture analysis for {person_name}: '{gesture}' (img: {img_time:.3f}s, gesture: {gesture_time:.3f}s)")
                                pubresults(cameraname, person_name, gesture)
                            else:
                                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: No suitable person found")
                                pubresults(cameraname, '', '')
                        else:
                            pubresults(cameraname, '', '')
                    else:
                        # Xử lý trực tiếp hình ảnh từ frigate
                        img_start_time = time.time()
                        img = getlatestimg(cameraname)
                        img_time = time.time() - img_start_time
                        
                        gesture_start_time = time.time()
                        gesture = gesturemodelfunctions.gesturemodelmatch(img)
                        gesture_time = time.time() - gesture_start_time
                        
                        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: Direct gesture analysis: '{gesture}' (img: {img_time:.3f}s, gesture: {gesture_time:.3f}s)")
                        # Vì không có thông tin người dùng, trường person sẽ để trống
                        pubresults(cameraname, '', gesture)
                    
                    total_process_time = time.time() - process_start_time
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: Total processing time: {total_process_time:.3f}s")
                except Exception as e:
                    total_process_time = time.time() - process_start_time
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Error processing camera {cameraname} after {total_process_time:.3f}s: {str(e)}")
                    import traceback
                    traceback.print_exc()
            elif numcamerapeople == 0:
                # Không cần log nếu số người vẫn là 0, đã được xử lý bởi việc kiểm tra thay đổi ở trên
                pubresults(cameraname, '', '')
        
        gc.collect()
        time.sleep(0.5)

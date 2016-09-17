# -*- coding: utf-8 -*-
import json
import uuid
import logging
import threading
from WebCurl.WebCurl import *
# from WaveOperate.WavePlot import *
# from WaveOperate.AudioPlay import *
from WaveOperate.AudioRecord import *
try:
    from io import BytesIO as StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
from ConfigFileInfoParser.InitializationConfigParser import InitializationConfigParser



def get_baidu_api_key_config(path):
    ini_Parser = InitializationConfigParser(path)
    Client_Credentials = ini_Parser.GetAllNodeItems("ClientCredentials")
    api_key = Client_Credentials.get("api_key")
    secret_key = Client_Credentials.get("secret_key")
    return api_key, secret_key

def get_baidu_token_config(path):
    ini_Parser = InitializationConfigParser(path)
    Client_Credentials = ini_Parser.GetAllNodeItems("ClientCredentials")
    access_token = Client_Credentials.get("access_token")
    return access_token

def get_baidu_token_url(api_key, secret_key):
    auth_url = "https://openapi.baidu.com/oauth/2.0/token?grant_type=client_credentials&client_id=" + api_key + "&client_secret=" + secret_key
    response = get_page_data(auth_url)
    json_str = str(response.decode())
    json_data = json.loads(json_str)
    access_token = json_data.get('access_token')
    return access_token

def save_baidu_token_config(path, access_token):
    ini_Parser = InitializationConfigParser(path)
    ini_Parser.SetOneKeyValue("ClientCredentials","access_token",access_token)

def get_mac_address():
    mac=uuid.UUID(int = uuid.getnode()).hex[-12:]
    return "-".join([mac[e:e+2] for e in range(0,11,2)])

class BaiduSpeechRecognition:
    def __init__(self, token, sonic_conf, record_conf):
        self.token = token
        self.sonic_conf = sonic_conf
        self.record_conf = record_conf
        self.cuid = get_mac_address() #用户 ID，推荐使用设备mac 地址/手机IMEI 等设备唯一性参数

    def post_recognition(self,record):
        wave_channels = self.sonic_conf.get('wave_channels', 1) #声道数
        sample_width = self.sonic_conf.get('sample_width', 2)   #量化宽度(byte)
        sample_frequency = self.sonic_conf.get('sample_frequency', 16000)#采样频率
        wave_buffer = record.get('bin_data')
        sample_length = record.get('sample_length')
        if not wave_buffer or wave_channels is not 1:
            raise Exception("wave_channels only support 1!")
        if isinstance(wave_buffer, list):
            audio_data = bytearray()
            for data in wave_buffer:
                audio_data.extend(data)
            audio_data = bytes(audio_data)
        elif not isinstance(wave_buffer, bytes):
            raise Exception("Type of bin_data need bytes!")
        else:
            audio_data = wave_buffer
        bin_data_length = sample_length * sample_width
        voice_service_url = 'http://vop.baidu.com/server_api' + '?cuid=' + self.cuid + '&token=' + self.token #+ '&lan=en'
        head = [
            'Content-Type: audio/pcm; rate=%d' % sample_frequency,
            'Content-Length: %d' % bin_data_length
        ]
        logging.info("Post start")
        page_data = post_page_data(voice_service_url, audio_data, head)
        logging.debug(page_data.decode())
        logging.info("Post end")
        json_data = json.loads(page_data.decode())
        err_no = json_data.get('err_no')
        if err_no:
            err_msg = json_data.get('err_msg')
            logging.debug("Speech recognition ERROR!")
            logging.debug("Error! " + err_msg)
            return err_no, "Error! " + err_msg
        else:
            result = json_data.get('result')
            logging.debug(result)
            return err_no, result

    def speech_recognition(self):
        recorder = AudioRecorder(self.sonic_conf)
        recording = recorder.recording(self.record_conf)
        for sonic in recording:
            yield self.post_recognition(sonic)

    def wav_file_recognition(self, filename):
        sonic = wav_file_read(filename)
        if 'bin_data' in sonic:
            return self.post_recognition(sonic)

    def recognition_thread(self, sonic, callback = None, traceback = None):
        err_no, result = self.post_recognition(sonic)
        if err_no:
            if traceback:
                traceback(result)
        else:
            if callback:
                callback(err_no, result)

    def speech_callback_recognition(self, callback = None, traceback = None):
        recorder = AudioRecorder(self.sonic_conf)
        recording = recorder.recording(self.record_conf)
        for sonic in recording:
            post_thread = threading.Thread(target=self.recognition_thread, args=(sonic, callback, traceback))
            post_thread.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    baidu_oauth_conf = 'BaiduOAuth.ini'
    # api_key, secret_key = get_baidu_api_key_config(baidu_oauth_conf)
    # access_token = get_baidu_token_url(api_key, secret_key)
    # save_baidu_token_config(baidu_oauth_conf, access_token)
    access_token = get_baidu_token_config(baidu_oauth_conf)
    sonic_conf = {
        'wave_channels':1,
        'sample_width':2,
        'sample_frequency':16000,
        'block_size':2000
    }
    record_conf = {
        'threshold_value':600,
        'series_min_count':30,
        'block_min_count':8
    }
    logging.warning("speech recognition record start.")
    speech_recognizer = BaiduSpeechRecognition(access_token, sonic_conf, record_conf)
    # for err_no, result in speech_recognizer.speech_recognition():
    #     print(err_no, result)
    speech_recognizer.speech_callback_recognition(print, print)



















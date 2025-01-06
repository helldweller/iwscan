from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
import re
import cgi
import sys
import json
import time
import subprocess

def parseiwscan(iw_output):
    output = {}
    for line in iw_output.splitlines():
        obj = {"ssid":"", "signal":"", "freq":"", "channel":"", "stations":"0" }
        if re.search("^BSS", line):
            regex = r'(([0-9a-f]{2}[:-]){5}([0-9a-f]){2})'
            if (re.findall(regex, line)[0][0]):
                bss = re.findall(regex, line)[0][0]
            else:
                continue
            output[bss] = obj
        if re.search("^\tSSID:", line):
            output[bss]["ssid"] = re.findall(r'(?:^\tSSID: )(.*)', line)[0]
        if re.search("^\tsignal:", line):
            output[bss]["signal"] = re.findall(r'(?:^\tsignal: )(.*)(?:\ .*)', line)[0]
        if re.search("^\tfreq:", line):
            output[bss]["freq"] = re.findall(r'(?:^\tfreq: )([0-9]*)', line)[0]
        if re.search("^[\ |\t]*\*\ primary\ channel:", line):
            output[bss]["channel"] = re.findall(r'(?:^[\ |\t]*\*\ primary\ channel: )([0-9]*)', line)[0]
        if re.search("^\t\t\ \*\ station\ count:", line):
            output[bss]["stations"] = re.findall(r'(?:^\t\t\ \*\ station\ count: )([0-9]*)', line)[0]
    return output

def json2prom(parsed):
    output1 = "# HELP wifi_ssids All scanned SSIDs with their signal quality.\n"
    output1 += "# TYPE wifi_ssids gauge\n"
    output2 = "# HELP wifi_station_count All scanned SSIDs with their station count.\n"
    output2 += "# TYPE wifi_station_count gauge\n"
    for mac in parsed:
        if parsed[mac]["channel"] != "":
            channel = parsed[mac]["channel"]
        else:
            channel = "?"
            print(parsed[mac]["ssid"] + " has no channel data")
        output1 += "wifi_ssids{mac=\"" + mac + "\",ssid=\"" + parsed[mac]["ssid"] + "\",freq=\"" + parsed[mac]["freq"] + "\",channel=\"" + channel + "\"} " + parsed[mac]["signal"] + "\n"
        output2 += "wifi_station_count{mac=\"" + mac + "\",ssid=\"" + parsed[mac]["ssid"]  + "\"} " + parsed[mac]["stations"] + "\n"
    return output1 + output2

class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_GET(self):
        self._set_headers()
        command = ["iw", "wlan0", "scan"]
        result = subprocess.run(command, capture_output=True, text=True)
        ifscan = result.stdout
        parsed = parseiwscan(ifscan)
        metrics = json2prom(parsed)
        self.wfile.write(metrics.encode("utf-8"))

    def do_POST(self):
        self._set_headers()
        test = "please use HTTP GET"
        self.wfile.write(test.encode("utf-8"))

def run(server_class=HTTPServer, handler_class=Server, port=5024):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd on port %d...' % port)
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv
    
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()

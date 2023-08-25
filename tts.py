from bs4 import BeautifulSoup
import ctypes
from ctypes import wintypes
from ctypes import windll
from os import path, fsync, mkdir
from threading import Thread
from time import sleep
import pyogg
import re
import requests
import simpleaudio
import tkinter as tk
import tkinter.scrolledtext as st

def get_audio_link(url):
    with requests.get(url) as response:
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        pattern = r'//upload\.wikimedia\.org.*?\.ogg'
        for tag in soup.find_all('a', href=True):
            href = tag['href']
            if re.match(pattern, href):
                return 'https:' + href
    return ''

def download_audio(link, filename):
    user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0'}
    response = requests.get(link, headers=user_agent, stream=True)
    with open(filename, 'wb') as file:
        for chunk in response.iter_content(1024):
            if chunk:
                file.write(chunk)
                file.flush()
                fsync(file.fileno())
    if log_downloads.get():
        append_log(f'downloaded {filename} from {link}\n')

# https://github.com/TeamPyOgg/PyOgg/issues/53
def convert_pathname(pathname):
    size = 1024
    buffer = (ctypes.c_wchar * size)()
    lpwstr = ctypes.cast(buffer, wintypes.LPWSTR)
    windll.kernel32.GetShortPathNameW(
        pathname,
        lpwstr,
        size
    )
    return lpwstr.value

def play_audio(file_list):
    for file in file_list:
        if file == 'pause':
            sleep(1)
            continue
        short = convert_pathname(file)
        vorbis = pyogg.VorbisFile(short)
        simpleaudio.play_buffer(
            vorbis.buffer,
            vorbis.channels,
            2, # bytes per sample
            vorbis.frequency
        ) #.wait_done()
        length_multiplier = vorbis.buffer_length / 10000
        sleep(0.1 + (0.07 * length_multiplier))

def append_log(msg):
    logger_box.insert(tk.INSERT, msg, 'say')
    logger_box.see(tk.END)

def append_files(files, target, is_pause):
    files.append(target)
    if is_pause:
        files.append('pause')

def say():
    words = textbox.get()
    files = list()

    if not words:
        return

    logger_box.configure(state=tk.NORMAL)
    append_log(f'saying {words}\n')

    for word in words.split(' '):
        is_pause = False
        if word[-1] == ',':
            is_pause = True
            word = word[:-1]
        filename = word + '.ogg'
        target = path.join(folder, filename)
        if path.exists(target):
            append_files(files, target, is_pause)
        else:
            url = 'https://de.wiktionary.org/wiki/' + word
            link = get_audio_link(url)
            if link:
                download_audio(link, target)
                append_files(files, target, is_pause)
            else:
                append_log(f'no link found for {url}! skipping...\n')
    
    logger_box.configure(state=tk.DISABLED)
    play_audio(files)

if __name__ == '__main__':
    folder = 'wikt-cache'
    if not path.exists(folder):
        mkdir(folder)

    root = tk.Tk()
    root.title('wikt-tts')
    root.geometry('510x380')
    root.bind('<Return>', lambda event: Thread(target=say).start())

    log_downloads = tk.BooleanVar(value=True)
    log_downloads_checkbox = tk.Checkbutton(
        root,
        text='Log downloads',
        variable=log_downloads
    )

    frame = tk.Frame(root)
    frame.grid()

    textbox = tk.Entry(frame, width=50)
    textbox.grid(column=0, row=0)
    textbox.focus_set()

    say_button = tk.Button(
        frame,
        text='Say',
        command=lambda: Thread(target=say).start()
    )
    say_button.grid(column=1, row=0, padx=5)

    log_downloads_checkbox.grid(column=0, row=1)
    
    logger_box = st.ScrolledText(root, state=tk.DISABLED, font=('Consolas', 8))
    logger_box.grid(column=0, row=2, padx=5, pady=5)
    
    root.mainloop()

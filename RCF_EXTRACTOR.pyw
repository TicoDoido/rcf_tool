import struct
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("RCF Files", "*.rcf"), ("All Files", "*.*")])
    if file_path:
        extract_files(file_path)
        
def calculate_padding(size, allocation=512):
    if size % allocation == 0:
        return size
    return ((size // allocation) + 1) * allocation

def select_rcf_file():
    rcf_path = filedialog.askopenfilename(filetypes=[("RCF Files", "*.rcf")])
    if rcf_path:
        select_txt_file(rcf_path)

def select_txt_file(rcf_path):
    base_filename = os.path.splitext(os.path.basename(rcf_path))[0]
    txt_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")], initialfile=f"{base_filename}.txt")
    if txt_path:
        recreate_rcf(rcf_path, txt_path)

def log_message(message):
    text_log.config(state=tk.NORMAL)
    text_log.insert(tk.END, message + '\n')
    text_log.config(state=tk.DISABLED)
    text_log.see(tk.END)  # Auto-scroll to the last line
    text_log.update()  # Force immediate log area update

def recreate_rcf(original_file_path, txt_names_path):
    base_filename = os.path.splitext(os.path.basename(original_file_path))[0]
    base_directory = os.path.dirname(original_file_path)
    new_rcf_path = os.path.join(base_directory, f"new_{base_filename}.rcf")

    # Directory where the extracted files are located
    extracted_files_directory = os.path.join(base_directory, base_filename)

    # Check if the directory exists
    if not os.path.exists(extracted_files_directory):
        messagebox.showerror("Error", f"Folder {extracted_files_directory} not found!")
        return

    log_message("Starting RCF file recreation...")
    with open(original_file_path, 'rb') as original_file:
        original_file.seek(32)
        file_version = original_file.read(4)

        if file_version == b'\x02\x01\x00\x01':
            log_message("Version is 02 01 00 01\nLITTLE ENDIAN MODE")
        elif file_version == b'\x02\x01\x01\x01':
            log_message("Version is 02 01 01 01\nBIG ENDIAN MODE")
        else:
            messagebox.showerror("Error", "Unsupported file!")
            return  
            
        if file_version == b'\x02\x01\x00\x01':
            original_file.seek(44)
            offset_value = struct.unpack('<I', original_file.read(4))[0]
            original_file.seek(48)
            size_value = struct.unpack('<I', original_file.read(4))[0]
        else:
            original_file.seek(44)
            offset_value = struct.unpack('>I', original_file.read(4))[0]
            original_file.seek(48)
            size_value = struct.unpack('>I', original_file.read(4))[0]

        header_size = offset_value + size_value
        adjusted_header_size = calculate_padding(header_size)

        original_file.seek(0)
        header = original_file.read(adjusted_header_size)

    with open(new_rcf_path, 'wb') as new_rcf:
        new_rcf.write(header)
        log_message(f"New header successfully written to {new_rcf_path}")

        pointers = []
        current_position = adjusted_header_size

        with open(txt_names_path, 'r', encoding='utf-8') as txt_names:
            for line in txt_names:
                file_name = line.strip()

                file_path = os.path.join(extracted_files_directory, file_name)
                if not os.path.exists(file_path):
                    log_message(f"File {file_name} not found!")
                    continue

                with open(file_path, 'rb') as f_file:
                    file_data = f_file.read()

                original_size = len(file_data)
                size_with_padding = calculate_padding(original_size)

                new_rcf.write(file_data)
                new_rcf.write(b'\x00' * (size_with_padding - original_size))

                pointers.append((current_position, original_size))
                current_position += size_with_padding

                log_message(f"File {file_name} added successfully.")

        new_rcf.seek(60)
        for pointer, original_size in pointers:
            new_rcf.seek(4, os.SEEK_CUR)
            if file_version == b'\x02\x01\x00\x01':
                new_rcf.write(struct.pack('<I', pointer))
                new_rcf.write(struct.pack('<I', original_size))
            else:
                new_rcf.write(struct.pack('>I', pointer))
                new_rcf.write(struct.pack('>I', original_size))

        log_message(f"New RCF file successfully created at: {new_rcf_path}")
        messagebox.showinfo("DONE", f"New RCF file created at: {new_rcf_path}")

def extract_files(file_path):
    base_directory = os.path.dirname(file_path)
    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    extraction_directory = os.path.join(base_directory, base_filename)

    if not os.path.exists(extraction_directory):
        os.makedirs(extraction_directory)

    with open(file_path, 'rb') as file:
        file.seek(32)
        file_version = file.read(4)
        
        if file_version == b'\x02\x01\x00\x01':
            log_message("Version is 02 01 00 01\nLITTLE ENDIAN MODE")
        elif file_version == b'\x02\x01\x01\x01':
            log_message("Version is 02 01 01 01\nBIG ENDIAN MODE")
        else:
            messagebox.showerror("Error", "Unsupported file!")
            return  

        file.seek(36)  # Move to the initial position of the pointers
        if file_version == b'\x02\x01\x00\x01':
            pointers_offset = struct.unpack('<I', file.read(4))[0]
            pointers_size = struct.unpack('<I', file.read(4))[0]
            names_offset = struct.unpack('<I', file.read(4))[0]
            names_size = struct.unpack('<I', file.read(4))[0]
        else:
            pointers_offset = struct.unpack('>I', file.read(4))[0]
            pointers_size = struct.unpack('>I', file.read(4))[0]
            names_offset = struct.unpack('>I', file.read(4))[0]
            names_size = struct.unpack('>I', file.read(4))[0]

        log_message(f"Pointer Offset: {pointers_offset}, Size: {pointers_size}")
        log_message(f"Names Offset: {names_offset}, Size: {names_size}")

        file.seek(56)
        
        if file_version == b'\x02\x01\x00\x01':
            total_items = struct.unpack('<I', file.read(4))[0]
            log_message(f"Total Items: {total_items}")
        else:
            total_items = struct.unpack('>I', file.read(4))[0]
            log_message(f"Total Items: {total_items}")

        pointers = []

        file.seek(pointers_offset)
        for i in range(total_items):
            file.seek(4, os.SEEK_CUR)  # Skip the first 4 bytes
            if file_version == b'\x02\x01\x00\x01':
                file_offset = struct.unpack('<I', file.read(4))[0]
                file_size = struct.unpack('<I', file.read(4))[0]
            else:
                file_offset = struct.unpack('>I', file.read(4))[0]
                file_size = struct.unpack('>I', file.read(4))[0]
            pointers.append((file_offset, file_size))

        names = []
        file.seek(names_offset + 8)

        for i in range(total_items):
            file.seek(12, os.SEEK_CUR)
            name_size = struct.unpack('<I', file.read(4))[0]

            name_bytes = file.read(name_size)

            try:
                name = name_bytes.decode('utf-8').strip('\x00')
                names.append(name)
            except UnicodeDecodeError as e:
                log_message(f"Error decoding name: {e} - Bytes read: {name_bytes}")

            file.seek(3, os.SEEK_CUR)

        for i, (file_offset, file_size) in enumerate(pointers):
            file.seek(file_offset)
            data = file.read(file_size)

            file_name = names[i] if i < len(names) else f"file_{i}.bin"
            
            complete_path = os.path.join(extraction_directory, file_name)

            file_directory = os.path.dirname(complete_path)
            if file_directory and not os.path.exists(file_directory):
                os.makedirs(file_directory)

            with open(complete_path, 'wb') as f:
                f.write(data)

            log_message(f"File {complete_path} extracted successfully.")

        names_list_path = os.path.join(base_directory, f"{base_filename}.txt")
        with open(names_list_path, 'w', encoding='utf-8') as names_list:
            for name in names:
                names_list.write(name + '\n')

        log_message(f"File list saved at: {names_list_path}")

    messagebox.showinfo("DONE", f"Files successfully extracted to: {extraction_directory}")

# Create the main window
root = tk.Tk()
root.title("RCF Tool")
root.geometry("400x300")

# Add buttons to the window
btn_select_file = tk.Button(root, text="Extract from RCF", command=select_file)
btn_select_file.pack(pady=10)

btn_select_rcf = tk.Button(root, text="Recreate RCF", command=select_rcf_file)
btn_select_rcf.pack(pady=10)

# Add a text area to show log messages
text_log = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED)
text_log.pack(fill=tk.BOTH, expand=True)

root.mainloop()
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
    base_directory = base_directory.replace('\\', '/') #THIS IS NOT NECESSARY, BUT I COULD NOT IGNORE IT
    new_rcf_path = os.path.join(base_directory, f"new_{base_filename}.rcf")
    new_rcf_path = new_rcf_path.replace('\\', '/')

    # Directory where the extracted files are located
    extracted_files_directory = os.path.join(base_directory, base_filename)

    # Check if the directory exists
    if not os.path.exists(extracted_files_directory):
        messagebox.showerror("Error", f"Folder {extracted_files_directory} not found!")
        return

    # Check if txt_names_path exists
    if not os.path.exists(txt_names_path):
        messagebox.showerror("Error", f"File {txt_names_path} not found!")
        return

    log_message("Starting RCF file recreation...")
    
    with open(original_file_path, 'rb') as original_file:
        original_file.seek(32)
        file_version = original_file.read(4)

        # Process versions 2.1 (Little and Big Endian)
        if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:
            endian_format = '<' if file_version == b'\x02\x01\x00\x01' else '>'
            endian_type = "LITTLE ENDIAN" if endian_format == '<' else "BIG ENDIAN"
            log_message(f"Version is 2.1\n{endian_type} MODE")

            original_file.seek(44)
            offset_value = struct.unpack(f'{endian_format}I', original_file.read(4))[0]
            original_file.seek(48)
            size_value = struct.unpack(f'{endian_format}I', original_file.read(4))[0]

            header_size = offset_value + size_value
            adjusted_header_size = calculate_padding(header_size)

            original_file.seek(0)
            header = original_file.read(adjusted_header_size)

        # Process version 1.2
        elif file_version == b'\x01\x02\x00\x01':
            log_message("Version is 1.2\nLITTLE ENDIAN MODE.")
            
            endian_format = '<'  # Define the endian format for version 1.2
            
            original_file.seek(2048)
            total_items = struct.unpack('<I', original_file.read(4))[0]
            names_offset = struct.unpack('<I', original_file.read(4))[0]
            
            original_file.seek(names_offset + 4)
            
            for i in range(total_items):
                original_file.seek(4, os.SEEK_CUR)
                name_size = struct.unpack('<I', original_file.read(4))[0]
                name_bytes = original_file.read(name_size)
                
            header_size = original_file.tell()
            adjusted_header_size = calculate_padding(header_size)
            
            original_file.seek(0)
            header = original_file.read(adjusted_header_size)

        else:
            messagebox.showerror("Error", "Unsupported file!")
            return

    with open(new_rcf_path, 'w+b') as new_rcf:
        # Escrever o cabeçalho
        new_rcf.write(header)
        log_message(f"New header successfully written to {new_rcf_path}")
    
        pointers = []
        current_position = adjusted_header_size
    
        # Abrir o arquivo de texto contendo os nomes
        with open(txt_names_path, 'r', encoding='utf-8') as txt_names:
            for line in txt_names:
                file_name = line.strip()
    
                file_path = os.path.join(extracted_files_directory, file_name)
                if not os.path.exists(file_path):
                    log_message(f"File {file_name} not found!")
                    continue
    
                # Ler o arquivo extraído
                with open(file_path, 'rb') as f_file:
                    file_data = f_file.read()
    
                original_size = len(file_data)
                size_with_padding = calculate_padding(original_size)

                new_rcf.write(file_data)
                new_rcf.write(b'\x00' * (size_with_padding - original_size))
    
                # Armazenar o ponteiro e o tamanho original
                pointers.append((current_position, original_size))
                current_position += size_with_padding
    
                log_message(f"File {file_name} added successfully.")
    
        # Voltar e escrever os ponteiros e os tamanhos
        new_rcf.seek(32)
        file_version = new_rcf.read(4)
        
        if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:
            endian_format = '<' if file_version == b'\x02\x01\x00\x01' else '>'
            
            new_rcf.seek(60)
            for pointer, original_size in pointers:
                new_rcf.seek(4, os.SEEK_CUR)  # Skip 4 bytes
                new_rcf.write(struct.pack(f'{endian_format}I', pointer))
                new_rcf.write(struct.pack(f'{endian_format}I', original_size))
                
        else:
            # Version 1.2 (LITTLE ENDIAN) -- EXISTS A BIG ENDIAN VERSION ?
            new_rcf.seek(2064)
            for pointer, original_size in pointers:
                new_rcf.seek(4, os.SEEK_CUR)  # Skip 4 bytes
                new_rcf.write(struct.pack('<I', pointer))
                new_rcf.write(struct.pack('<I', original_size))
    
    log_message(f"New RCF file successfully created at: {new_rcf_path}")
    messagebox.showinfo("DONE", f"New RCF file created at: {new_rcf_path}")


def extract_files(file_path):
    base_directory = os.path.dirname(file_path)
    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    extraction_directory = os.path.join(base_directory, base_filename)
    extraction_directory = extraction_directory.replace('\\', '/')

    if not os.path.exists(extraction_directory):
        os.makedirs(extraction_directory)

    with open(file_path, 'rb') as file:
        file.seek(32)
        file_version = file.read(4)
        
        if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:
            if file_version == b'\x02\x01\x00\x01':
                log_message("Version is 2.1\nLITTLE ENDIAN MODE")
            else:
                log_message("Version is 2.1\nBIG ENDIAN MODE")

            file.seek(36)  # Move to the initial position of the pointers
            if file_version == b'\x02\x01\x00\x01':
                pointers_offset = struct.unpack('<I', file.read(4))[0]
                file.seek(4, os.SEEK_CUR)
                names_offset = struct.unpack('<I', file.read(4))[0]
                file.seek(4, os.SEEK_CUR)
            else:
                pointers_offset = struct.unpack('>I', file.read(4))[0]
                file.seek(4, os.SEEK_CUR)
                names_offset = struct.unpack('>I', file.read(4))[0]
                file.seek(4, os.SEEK_CUR)

            log_message(f"Pointer Offset: {pointers_offset}")
            log_message(f"Names Offset: {names_offset}")

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

        # Processo específico para a versão 01 02 00 01
        elif file_version == b'\x01\x02\x00\x01':
            log_message("Version is 1.2\nLITTLE ENDIAN MODE.")
            
            file.seek(2048)
            total_items = struct.unpack('<I', file.read(4))[0]
            
            log_message(f"Total Items: {total_items}")
            
            names_offset = struct.unpack('<I', file.read(4))[0]
            
            file.seek(8, os.SEEK_CUR)
            
            pointers = []
            
            for i in range(total_items):
                file.seek(4, os.SEEK_CUR)  # Skip the first 4 bytes
                file_offset = struct.unpack('<I', file.read(4))[0]
                file_size = struct.unpack('<I', file.read(4))[0]
                pointers.append((file_offset, file_size))
                
            names = []
            
            file.seek(names_offset +4)
            
            for i in range(total_items):
                file.seek(4, os.SEEK_CUR)
                
                name_size = struct.unpack('<I', file.read(4))[0]

                name_bytes = file.read(name_size)

                try:
                    name = name_bytes.decode('utf-8').strip('\x00')
                    names.append(name)
                except UnicodeDecodeError as e:
                    log_message(f"Error decoding name: {e} - Bytes read: {name_bytes}")
            
            for i, (file_offset, file_size) in enumerate(pointers):
                file.seek(file_offset)
                data = file.read(file_size)

                file_name = names[i] if i < len(names) else f"file_{i}.bin"
                
                complete_path = os.path.join(extraction_directory, file_name)
                complete_path = complete_path.replace('\\', '/')

                file_directory = os.path.dirname(complete_path)
                if file_directory and not os.path.exists(file_directory):
                    os.makedirs(file_directory)

                with open(complete_path, 'wb') as f:
                    f.write(data)

                log_message(f"File {complete_path} extracted successfully.")

            names_list_path = os.path.join(base_directory, f"{base_filename}.txt")
            names_list_path = names_list_path.replace('\\', '/')
            with open(names_list_path, 'w', encoding='utf-8') as names_list:
                for name in names:
                    names_list.write(name + '\n')

            log_message(f"File list saved at: {names_list_path}")

        else:
            messagebox.showerror("Error", "Unsupported file!")
            return  

    messagebox.showinfo("DONE", f"Files successfully extracted to: {extraction_directory}")

root = tk.Tk()
root.title("RCF Tool")
root.geometry("400x300")

btn_select_file = tk.Button(root, text="Extract from RCF", command=select_file)
btn_select_file.pack(pady=10)

btn_select_rcf = tk.Button(root, text="Recreate RCF", command=select_rcf_file)
btn_select_rcf.pack(pady=10)

text_log = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED)
text_log.pack(fill=tk.BOTH, expand=True)

root.mainloop()

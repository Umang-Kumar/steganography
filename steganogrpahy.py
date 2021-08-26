import cv2  # pip install opencv-python
import os

split_byte_to_bits = lambda data: [data >> 5, (data >> 2) & 0x7, data & 0x3]
extract_nbits_of_byte = lambda band, n: band & (2 ** n - 1)
merge_bits = lambda rbits, gbits, bbits: (((rbits << 3) | gbits) << 2) | bbits


def generate_embedded_imagename(vessel_img):
	# vessel image:- c:/images/kids.jpg
	# embedded image:- c:/images/e_kids.png
	if '/' in vessel_img:
		temp = vessel_img.split('/')  # ['c:', 'images', 'kids.jpg']
		temp[-1] = 'e_' + temp[-1]  # ['c:', 'images', 'e_kids.jpg']
		ename = '/'.join(temp)  # c:/images/e_kids.jpg
		if ename.lower().endswith('.jpg'):
			ename = ename.replace('.jpg', '.png')
		elif ename.lower().endswith('.jpeg'):
			ename = ename.replace('.jpeg', '.png')
		return ename
	else:
		print('Use / as separator')
		return None


def generate_header(doc):
	# 20 bytes name + 10 bytes size
	# d:/imp_content/secret.docx
	name = doc.split('/')[-1]  # [d:, imp_content, secret.docx]

	l = len(name)
	if l > 20:
		name = name[l - 20:]  # trim
	elif l < 20:
		name = name.rjust(20, '*')  # pad

	size = str(os.path.getsize(doc))
	size = size.rjust(10, '*')
	return name + size


def embed(vessel_image, doc):
	# does the vessel_img and the doc exist?
	if not os.path.exists(vessel_image):
		print(vessel_image, 'not found')
		return None
	if not os.path.exists(doc):
		print(doc, 'not found')
		return None

	# load the image in memory
	mem_image = cv2.imread(vessel_image, cv2.IMREAD_COLOR)
	# type(mem_image) --> numpy.ndarray
	# mem_image.shape --> height, width, pixelsize(bgr)
	h, w, _ = mem_image.shape

	# know the size of the document
	doc_size = os.path.getsize(doc)

	# generate the header
	header = generate_header(doc)

	# test the embedding capacity
	capacity = h * w
	header_length = len(header)

	if doc_size + header_length > capacity:
		print(doc, ' too large to fit in', vessel_image)
		return None

	# embed
	cnt = 0
	# open the file for reading in binary mode (to support reading all file types)
	file_handle = open(doc, 'rb')

	flag = True
	i = 0
	while i < h and flag:  # for each row
		j = 0
		while j < w and flag:  # for each col of the row i
			# fetch a pixel
			pixel = mem_image[i, j]
			blue = pixel[0]
			green = pixel[1]
			red = pixel[2]

			if cnt < header_length:
				# fetch a byte from the header
				data = ord(header[cnt])
			else:
				# fetch a byte from the file
				data = file_handle.read(1)
				if data:  # test
					# data fetched is in the form: byte object
					# it needs conversion into int
					data = int.from_bytes(data, byteorder='big')
				else:
					# its the EOF(end of the file)
					flag = False  # stop embedding
					continue

			bits = split_byte_to_bits(data)

			# embed the bits
			red = (red & (~0x7)) | bits[0]
			green = (green & (~0x7)) | bits[1]
			blue = (blue & (~0x3)) | bits[2]

			# update the mem_image_pixel[i,j]
			mem_image[i, j, 0] = blue
			mem_image[i, j, 1] = green
			mem_image[i, j, 2] = red

			cnt += 1  # next byte
			j += 1  # col change
		i += 1  # row change

	file_handle.close()
	# save back
	target_image = generate_embedded_imagename(vessel_image)
	cv2.imwrite(target_image, mem_image)

	return target_image


def extract(embedded_image, target_folder):
	if not os.path.exists(embedded_image):
		print(embedded_image, 'not found')
		return None
	if not os.path.exists(target_folder):
		print(target_folder, 'not found')
		return None

	# load the image in memory
	mem_img = cv2.imread(embedded_image, cv2.IMREAD_COLOR)

	# fetch the size
	h, w, _ = mem_img.shape

	header_length = 30
	flag = True
	i = 0
	cnt = 0
	header = ''
	while i < h and flag:  # for each row
		j = 0
		while j < w and flag:  # for each col of row i
			# fetch a pixel
			pixel = mem_img[i, j]
			blue = pixel[0]
			green = pixel[1]
			red = pixel[2]

			# extract 3,3,2 bits of the bands (r,g,b) of the pixel
			red_bits = extract_nbits_of_byte(red, 3)
			green_bits = extract_nbits_of_byte(green, 3)
			blue_bits = extract_nbits_of_byte(blue, 2)

			# merge the bits to form the byte
			data = merge_bits(red_bits, green_bits, blue_bits)

			if cnt < header_length:
				header = header + chr(data)
			else:
				if cnt == header_length:  # header processing
					print(header)
					filename = header[:20].strip('*')
					filesize = int(header[20:].strip('*'))

					# open the file for writing
					file_handle = open(target_folder + '/' + filename, 'wb')

				if cnt - header_length < filesize:
					# data is a numpy.int
					# convert it into py int
					# convert py int into byte object
					data = int.to_bytes(int(data), 1, byteorder='big')
					# write to the file (byte objects)
					file_handle.write(data)
				else:
					file_handle.close()
					flag = False

			cnt += 1
			j += 1
		i += 1
	return target_folder + '/' + filename


def main():
	while True:
		print('1. Embed')
		print('2. Extract')
		print('3. Exit')
		print('Enter Choice ')
		ch = int(input())

		if ch == 1:
			print('Enter vessel image path')
			vessel_img = input()
			print('Enter file to embed')
			doc = input()

			result = embed(vessel_img, doc)
			if result is not None:
				print('Embedding Done, result: ', result)
			else:
				print('Embedding Failed')
		elif ch == 2:
			print('Enter embedded image path')
			embedded_image = input()
			print('Enter target folder for saving the extracted file')
			target_folder = input()

			result = extract(embedded_image, target_folder)
			if result is not None:
				print('Extraction Done, result: ', result)
			else:
				print('Extraction Failed')
		elif ch == 3:
			break
		else:
			print('Wrong Choice')


main()

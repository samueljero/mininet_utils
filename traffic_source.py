#!/usr/bin/python
# Utility for taking traffic matricies generated with 
# DCT^2Gen---https://www.cs.uni-paderborn.de/fachgebiete/fachgebiet-rechnernetze/people/philip-wette-msc/dct2gen.html
# and generating TCP flows for that traffic.
# Has ability to specify a time dilation factor.
#
# Samuel Jero <sjero@purdue.edu>
# James Lembke <lembkej@purdue.edu>
# Nathan Burow <nburow@purdue.edu>
#
# Copyright (c) 2014
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software without
#    specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import sys
import re
import csv
import socket
import getopt
import threading
import select
import struct
from time import time
from time import sleep

client="h1"
port=1025
mat_time_inc=10

def usage():
	print "TrafficHost [-h] [-c client_num] [-p port] [-d dns_file] [-z zero_time] [-f time_dilation_factor] matrix_files"

def host_name2num(name):
	#return 1
	m = re.match(r"h(\d+)", name)
	if m is None:
		print "Error: returning none!"
		return None
	return int(m.group(1))

def host_num2name(ident):
	#return "127.0.0.1"
	return ("h%d" % ident)
	

def parse_dns(fname):
	db=[]
	f = open(fname)
	trafficreader = csv.reader(f, skipinitialspace=True,delimiter=',')
	for row in trafficreader:
		r = [row[0], row[1]]
		db.append(r)
	return db

def dns_lookup(dns, name):
	for r in dns:
		if name==r[0]:
			return r[1]
	print "Error: no DNS mapping for %s" % name
	return ""

def parse_mats(files, client, dns, tmdilation):
	global mat_time_inc
	rtime=0
	flows=[]
	timeoffset=0
	mynum=host_name2num(client)
	print "I am ID: " + str(mynum)
	for fn in files:
		f = open(fn)
		trafficreader = csv.reader(f, skipinitialspace=True,delimiter=',')
		for row in trafficreader:
			if int(row[0]) == mynum:
				hn= host_num2name(int(row[1]))
				if len(dns) > 0:
					hn = dns_lookup(dns, hn)
				flow = [float(row[2])*tmdilation, hn, int(float(row[3]))]
				flows.append(flow)
			if float(row[2]) > rtime:
				rtime = float(row[2])

	rtime = rtime * tmdilation
	return flows, rtime
	
def sort_flows(flows):
	return sorted(flows, key=lambda f: f[0])

class ReadThread (threading.Thread):
	def __init__(self, sock):
		threading.Thread.__init__(self)
		self.sock = sock[0]
	def run(self):
		t=time()
		d=0
		try:
			v = self.sock.recv(4096)
		except socket.error as e:
			print e
			self.sock.close()
			return 0
		if v:
			d = d + len(v)
		while v:
			v = ""
			try:
				v = self.sock.recv(4096)
			except socket.error as e:
				print e
				self.sock.close()
				return 0
			if v:
				d = d + len(v)
		self.sock.close()
		n = time()
		diff = float(n) - float(t)
		if  diff > 0:
			tput = (d*8) / diff
			#print "throughput: " + str(tput/1048576) + " Mbits/sec"

class AcceptThread (threading.Thread):
	def __init__(self, client, port, rtime, dns):
		threading.Thread.__init__(self)
		if len(dns) > 0:
			self.client = dns_lookup(dns, client)
		else:
			self.client = client
		self.port = port
		self.rtime= rtime
	def run(self):
		thds=[]

		#open listen socket
		l = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			l.bind((self.client, self.port))
			l.listen(20)
		except socket.error as e:
			print e
			l.close()
			return 0
		print "listening..." + self.client
		l.settimeout(3)

		end = time() + self.rtime + 10
		loops=0
		while time() < end:
			try:
				n = l.accept()
			except socket.timeout as t:
				continue
			except socket.error as e:
				print e
				return 0
			t = ReadThread(n)
			t.start()
			
			thds.append(t)

			#Cleanup
			loops=loops + 1
			if loops % 10 == 0:
				for t in thds:
					if t.is_alive() == False:
						t.join()
		#print "accept terminating"
		l.close()

		for t in thds:
			t.join()
		return 0
			
class SendThread (threading.Thread):
	def __init__(self, dst, sz, port):
		threading.Thread.__init__(self)
		self.port = port
		self.dst = dst
		self.sz = sz

	def run(self):
		#print "connecting..." + self.dst
		#create 4K of data to send
		data = ""
		for i in range(0,256):
			data= data + (str(struct.pack("B",i)))
		for i in range(0,4):
			data = data + data

		s =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			s.connect((self.dst,self.port))
		except socket.error as e:
			print e
			print self.dst
			s.close()
			return 0

		sntdata=0
		while sntdata < self.sz:
			diff = self.sz - sntdata
			if diff < 4096:
				try:
					snt = s.send(data[0:diff])
				except socket.error as e:
					print e
					print self.dst
					s.close()
					return 0
				sntdata = sntdata + snt
			else:
				try:
					snt = s.send(data)
				except socket.error as e:
					print e
					print self.dst
					s.close()
					return 0
				sntdata = sntdata + snt
		s.close()
		#print "closing..." + self.dst
		return 0
		

def do_test(flows, port, rtime, client, dns, zero):
	thds= []
	tdiff = 0
	if zero > 0:
		tdiff = zero - time()
	r = AcceptThread(client, port,rtime + tdiff, dns)
	r.start()
	
	nxt=0
	if zero > 0:
		tzero = zero
	else:
		tzero=time()
	while nxt < len(flows):
		tm = time()
		if tm - tzero < flows[nxt][0]:
			sleep(flows[nxt][0] - (tm - tzero))
		t = SendThread(flows[nxt][1], flows[nxt][2], port)
		t.start()
		thds.append(t)
		nxt = nxt + 1

	for t in thds:
		t.join()
	r.join()
	print "Testing finished"
	return 0
	
			
	

def main():
	global client,port, fancy_names
	dns = []
	zero = 0
	tmdilation = 1
	try:                                
		opts, args = getopt.getopt(sys.argv[1:], "hc:p:d:z:f", ["help","client=", "port=","dns=", "zero=", "dilation="])
	except getopt.GetoptError:
		usage()
		sys.exit(2)
	for opt,arg in opts:
		if opt in ("-c", "--client"):
			client=arg
		elif opt in ("-p", "--port"):
			port=int(arg)
		elif opt in ("-d", "--dns"):
			dfile=arg
			dns=parse_dns(dfile)
		elif opt in ("-z", "--zero"):
			zero=float(arg)
		elif opt in ("-f", "--dilation"):
			tmdilation=float(arg)
		elif opt in ("-h", "--help"):
			usage()
			sys.exit()
		else:
			print "Unknown Option"
			sys.exit()
	infiles=args
	if len(infiles)==0:
		print "Error, no matrices"
		sys.exit()
	flows, rtime=parse_mats(infiles, client,dns,tmdilation)
	flows=sort_flows(flows)
	do_test(flows,port, rtime, client,dns, zero)



if __name__ == '__main__':
	main()

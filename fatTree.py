# Fat-tree topology implementation for Mininet--http://mininet.org
# Based On:
# Al-Fares, M. et al. 2008. A Scalable, Commodity Data Center Network Architecture. ACM SIGCOMM Computer Communication Review. 38, (2008), 63.
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
import sys, random, re
from mininet.topo import Topo


class FatTree(Topo):
	def randByte(self):
		return hex(random.randint (0, 255))[2:]
		
	def makeMAC(self, i):
		return self.randByte() + ":" + self.randByte() + ":" + self.randByte() + ":00:00:" + hex (i)[2:]

	def makeDPID(self, i):
		a = self.makeMAC(i)
		dp = "".join(re.findall(r'[a-f0-9]+', a))
		return "0" * (12 - len(dp)) + dp

	def __init__(self, hpr = 20, racks = 2, bw = 10, **opts):
		Topo.__init__(self, **opts)
		if (racks % 2 != 0):
			print "Warning number of racks must be even!" 
		if (hpr % 4 != 0):
			print "Warning Hosts per Rack must be divisible by 4!"

		tor = []
		agg = []
		core = []
		numLeaf = hpr * racks 

		s = 1
		#ToR switches
		for i in range(racks):
			sw = self.addSwitch('s' + str (s), dpid = self.makeDPID(s), **dict(listenPort = (13000 + s - 1)))
			s = s + 1
			tor.append(sw)

		#End Hosts
		for i in range(numLeaf):
			h = self.addHost('h' + str(i + 1), mac = self.makeMAC(i), ip = "10.0." +  str((i+1)/255)+ "." + str ((i+1)%255))
			sw = tor[i / hpr]
			self.addLink(h, sw, bw = bw)
		#Pods
		for i in range(racks / 2):
			asw1 = self.addSwitch('s' + str(s), dpid = self.makeDPID(s), **dict(listenPort = (13000 + s - 1)))
			s = s + 1
			agg.append(asw1)
			asw2 = self.addSwitch('s' + str(s), dpid = self.makeDPID(s), **dict(listenPort = (13000 + s - 1))) 
			s = s + 1
			agg.append(asw2)
			tsw1 = tor[i * 2]
			tsw2 = tor[i * 2 + 1]
			#bw = bw * (hpr/4)
			self.addLink(tsw1, asw1)
			self.addLink(tsw1, asw2)
			self.addLink(tsw2, asw1)
			self.addLink(tsw2, asw2)

		#Core
		for i in range(racks / 2):
			csw = self.addSwitch('s' + str(s), dpid = self.makeDPID(s), **dict(listenPort = (13000 + s - 1)))
			s = s + 1
			core.append(csw)
		for i in range(0, len(agg), 2):
			for j in range(0, len(core) / 2):
				self.addLink(agg[i], core[j], bw = bw)
		for i in range(1, len (agg), 2):
			for j in range(len(core) / 2, len(core)):
				self.addLink(agg[i], core[j], bw = bw)


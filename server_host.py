# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# Mininet host that runs iperf and webservers as well as randomly
# picking another host and running an iperf or web client.
#
# Samuel Jero <sjero@purdue.edu>
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
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, Controller, RemoteController, Host
from mininet.topolib import TreeTopo
from mininet.log import lg
from time import time, sleep
from mininet.cli import CLI
import subprocess
import os
import threading
import random


class ClientThread(threading.Thread):
    def __init__(self, nm, me, hosts):
        threading.Thread.__init__(self,name=nm)
        self.hosts = hosts
        self.me = me
        self.done = False
        self.prog = None

    def run(self):
        while not self.done:
            r = random.randint(0,2)
            print self.me.name + "r=" + str(r)
            if r == 0:
                dst = random.choice(self.hosts)
                tm = random.randint(2,30)
                self.prog = self.me.popen(["/usr/bin/iperf", "-c", dst.IP(), "-t", str(tm)], stdout=open(os.devnull,"w"), stderr=subprocess.STDOUT)
                self.prog.wait()
                self.prog = None
            elif r == 1:
                dst = random.choice(self.hosts)
                #Big is 100MB, small is 10K
                urls = ["/big", "/small"]
                u = random.choice(urls)
                self.prog = self.me.popen(["/usr/bin/curl","-o", "/dev/null", "http://" + dst.IP() + u], stdout=open(os.devnull,"w"), stderr=subprocess.STDOUT)
                self.prog.wait()
                self.prog = None
            elif r == 2:
                sleep(random.randint(2,30))
            

    def stop(self):
        self.done = True
        if self.prog is not None:
            self.prog.terminate()
            self.prog.kill()

class TestHost(Host):
    def __init__(self, name, **kwargs):
        Host.__init__(self, name, **kwargs)
        self.iperf_server = None
        self.web_server = None
        self.client = None

    def start1(self):
        print "Start Servers: " + self.name
        self.iperf_server = self.popen(["/usr/bin/iperf", "-s"],stdout=open(os.devnull,"w"),stderr=subprocess.STDOUT)
        self.web_server = self.popen(["/usr/bin/python", "-m", "SimpleHTTPServer", "80"],stdout=open(os.devnull,"w"),stderr=subprocess.STDOUT)

    def start2(self, hosts):
        self.client = ClientThread(self.name + "-cl", self, hosts)
        self.client.start()

    def stop1(self):
        if self.client is not None:
            self.client.stop()
        if self.iperf_server is not None:
            self.iperf_server.terminate()
        if self.web_server is not None:
            self.web_server.terminate()
        pass

def main():
    lg.setLogLevel( 'info' )

    #Setup network
    ctl = RemoteController("c1",ip='10.0.1.1',port=6633)
    network = Mininet(topo=TreeTopo(2,2), controller=ctl, switch=OVSKernelSwitch, host=TestHost)
    network.start()

    #Topology detection delay
    sleep(30)

    for h in network.hosts:
        h.start1()
    for h in network.hosts:
        h.start2(network.hosts)

    sleep(300)
    network.pingAll()

    #Stop network
    for h in network.hosts:
        h.stop1()
    network.stop()
        

if __name__ == '__main__':
    main()  

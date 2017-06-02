# Mininet Utilities
Useful utlities for use in emulating data center networks with Mininet

Contents:
* **traffic_source.py**--A script to generate TCP traffic from traffic matricies generated with DCT^2Gen by Philip Wette and Holger Karl (https://www.cs.uni-paderborn.de/fachgebiete/fachgebiet-rechnernetze/people/philip-wette-msc/dct2gen.html)
* **fatTree.py**--A Fat Tree topology implementation for Mininet based on: Al-Fares, M. et al. 2008. A Scalable, Commodity Data Center Network Architecture. ACM SIGCOMM Computer Communication Review. 38, (2008), 63.
* **twoTierTree.py**--A Two Tier Tree topology implementation for mininet
* **threeTierTree.py**--A Three Tier Tree topology implementation for mininet
* **server_host.py**--An implementation of a host that runs web and iperf servers and then connects randomly to another host using either web or iperf clients

## License
All of this code is licensed under the BSD license. See the LICENSE file for details.

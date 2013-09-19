#! /usr/bin/env python

'''
Copyright (C) pybtchat  Angelo Poerio <angelo.poerio@gmail.com>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import gtk
from bluetooth import *
import threading
import sys
import random
import gobject
import pynotify
import Queue

gtk.gdk.threads_init()

class BtServer(threading.Thread):
	
	def __init__(self,widget,status,client):
		threading.Thread.__init__(self)
		self.widget = widget
		self.sock = 0
		self.status = status
		self.client = client
		self.exit = False
		self.notification = False

	def makeServer(self):
		self.sock=BluetoothSocket(RFCOMM)
		self.sock.settimeout(2.0)
		self.sock.bind(('', 1))
		self.sock.listen(1)
	
	def run(self):
		self.makeServer()

		while True:
			try:
				(conn,addr) = (0,0)
				(conn, addr) = self.sock.accept()

			except BluetoothError:
						
				if self.exit == True:
					sys.exit(0)

			if (conn,addr) == (0,0):
				continue

			self.client.set_someconnected()
			gtk.gdk.threads_enter()
			self.status.push(1,str(addr[0])+" is connected to you")
			gtk.gdk.threads_leave()

			while True:
				
				data = ""
				
				try:
					conn.settimeout(2.0)
					data = conn.recv(1024)
					
				except BluetoothError as error:

					if self.exit == True:	
						conn.close()
						self.sock.close()
						sys.exit(0)

					if error.__str__().rfind("timed out") == -1:
						conn.close()
						self.client.set_notconnected()
						self.client.unset_someconnected() 
						break
				

				if self.exit == True:
					conn.close()
					self.sock.close()	
					sys.exit(0)

				gtk.gdk.threads_enter()
				
				if len(data) > 1:
					self.widget.get_buffer().insert_at_cursor("\n"+data)

					if self.notification:
						n = pynotify.Notification("pybtchat","You got a new message!")
						n.set_icon_from_pixbuf(gtk.gdk.pixbuf_new_from_file("pics/icon.png"))
						n.show()	
					
				
				gtk.gdk.threads_leave()
				
	
	def set_notification(self):
		self.notification = True

	def unset_notification(self):
		self.notification = False
	

	def KillServer(self):
		self.exit = True


class BTClient():

	def __init__(self,textentry,widget,status):
		self.sock=None
		self.widget = widget
		self.status = status
		self.connected = False
		self.msg = textentry
		self.nick = ""
		self.watch_id = 0
		self.some_connected = False

	def set_nick(self,nick):
		self.nick = nick

	def set_connected(self,addr):
		self.connected = True
		self.status.push(1,"Connected to "+addr)

	def set_notconnected(self):
		self.connected = False
		
		if self.sock is not None:
			self.sock.close()
		
		self.status.push(1,"Not connected")

	def check_connection(self,source,condition):
		self.set_notconnected()
		gobject.source_remove(self.watch_id)
		return False

	def set_someconnected(self):
		self.some_connected = True
	
	def unset_someconnected(self):
		self.some_connected = False

	def connect(self,addr):

		if self.connected == True:
			warning_dlg = gtk.MessageDialog(type=gtk.MESSAGE_WARNING,message_format="You are already connected to "+addr,buttons=gtk.BUTTONS_OK)
			warning_dlg.set_icon(gtk.gdk.pixbuf_new_from_file("pics/icon.png"))  			
			warning_dlg.run()
			warning_dlg.destroy()
			return

		try:
			self.sock=BluetoothSocket(RFCOMM )
			self.sock.connect((addr,1))
		except:
			error_dlg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,message_format="Error connecting to "+addr,buttons=gtk.BUTTONS_OK)
			error_dlg.set_icon(gtk.gdk.pixbuf_new_from_file("pics/icon.png"))  			
			error_dlg.run()
			error_dlg.destroy()
			self.set_notconnected()
			return False
		
		self.watch_id = gobject.io_add_watch(self.sock,gobject.IO_HUP|gobject.IO_ERR,self.check_connection)
		self.set_connected(addr)
		return True

	def reader(self,widget):
		try:
			if self.connected:
				data = self.msg.get_text()
				self.msg.set_text("")

				if(len(data) > 1):
					self.widget.get_buffer().insert_at_cursor("\n<"+self.nick+"> "+ data)	
					self.sock.send("<"+self.nick+"> "+data)

				if self.some_connected == False:
					self.status.push(1,"The other user is not yet connected to you!")
	
			else:
				self.widget.get_buffer().insert_at_cursor("\nNot connected")
				self.msg.set_text("")
		
		except:
			error_dlg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,message_format="Can't send the message",buttons=gtk.BUTTONS_OK)
			error_dlg.set_icon(gtk.gdk.pixbuf_new_from_file("pics/icon.png"))  			
			error_dlg.run()
			error_dlg.destroy()
			self.set_notconnected()

	def kill_client(self):
		if self.sock is not None:
			self.set_notconnected()
			
class BTDiscover(threading.Thread):
	
	def __init__(self,widget,status,queue,queue2):
		threading.Thread.__init__(self)
		self.widget = widget
		self.status = status
		self.queue = queue
		self.queue2 = queue2

	def run(self):
		gtk.gdk.threads_enter()
		self.widget.clear()
		self.status.push(1,"Discovering...")
		gtk.gdk.threads_leave()
		
		if self.queue.empty() == False:
			sys.exit(0)

		try:		
			nearby_devices = discover_devices(lookup_names = True)
		except:
			self.status.push(1,"Can't lookup for devices!")
			return

		if self.queue.empty() == False:
			sys.exit(0)

		gtk.gdk.threads_enter()
		cnt = 0		

		if self.queue.empty() == False:
			sys.exit(0)

		self.widget.clear()

		for addr, name in nearby_devices:
			self.widget.insert(cnt,[name,addr])
			cnt = cnt + 1

		self.status.push(1,"Done")
		self.queue2.get()
		self.queue2.task_done()

		if self.queue.empty() == False:
			sys.exit(0)
		
		gtk.gdk.threads_leave()

		if self.queue.empty() == False:
			sys.exit(0)

class Gui:		

	def delete_event(self, widget, event, data=None):
		self.server.KillServer()
		self.client.kill_client()	
		self.queue.put(True)	
		self.queue.put(True)
		self.queue.put(True)
		return False
	
	def destroy(self, widget, data=None):
		self.server.KillServer()
		self.client.kill_client()
		self.queue.put(True)	
		self.queue.put(True)
		self.queue.put(True)
		gtk.main_quit()

	def icon(self,widget,event,data=None):
		if event.changed_mask & gtk.gdk.WINDOW_STATE_ICONIFIED:
      			if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
				self.server.set_notification()
			else:
				self.server.unset_notification()
				

	def clear_chat(self,widget):
		self.textview_chat.get_buffer().set_text("")

	def lookup(self,widget):
		if self.queue2.empty() == True:
			self.queue2.put(True)
 			discover = BTDiscover(self.list_devices,self.status,self.queue,self.queue2)
			discover.start()

	def row_connect(self,treeview, iter, path, user_data):
		model=treeview.get_model()
    		iter = model.get_iter(iter)
    		addr = model.get_value(iter, 1)
	
		if len(addr) > 1:
			self.client.connect(addr)

	def disconnect(self,widget):
		self.client.kill_client()

	def InputBox(self,title, label, parent, text=''):
    		dlg = gtk.Dialog(title, parent, gtk.DIALOG_DESTROY_WITH_PARENT,(gtk.STOCK_OK, gtk.RESPONSE_OK,gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
		dlg.set_icon(gtk.gdk.pixbuf_new_from_file("pics/icon.png"))    		
		lbl = gtk.Label(label)
    		lbl.show()
    		dlg.vbox.pack_start(lbl)
    		entry = gtk.Entry()
    		if text: 
			entry.set_text(text)
    		
		entry.show()
    		dlg.vbox.pack_start(entry, False)
    		resp = dlg.run()
    		text = entry.get_text()
    		dlg.hide()
    		
		if resp == gtk.RESPONSE_CANCEL:
			return None
		
		return text


	def change_nick(self,widget):
		nick = self.InputBox('Set your nickname','Nick:',None)
		
		if nick is not None:
			if len(nick) > 0:			
				self.set_nick(nick)

	def set_nick(self,nick):
		self.change_nick_button.set_label(nick)
		self.client.set_nick(nick)

	def about(self,widget):
		about = gtk.AboutDialog()
        	about.set_program_name("pybtchat")
        	about.set_version("0.2.3")
        	about.set_copyright("(c) Angelo Poerio")
        	about.set_comments("pybtchat is a simple chat program (one to one) that uses bluetooth technology")
        	about.set_website("http://pybtchat.sourceforge.net")
		about.set_authors(["Angelo Poerio <angelo.poerio@gmail.com>"])
		about.set_icon(gtk.gdk.pixbuf_new_from_file("pics/icon.png"))
		about.set_license('''
Copyright (C) pybtchat  Angelo Poerio <angelo.poerio@gmail.com>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
		''')

        	about.set_logo(gtk.gdk.pixbuf_new_from_file("pics/icon.png"))
        	about.run()
        	about.destroy()

	def __init__(self):
	        builder = gtk.Builder()
	   	builder.add_from_file("xml/pybtchat.xml")
	    	self.window = builder.get_object("main_window")
		self.window.set_icon_from_file("pics/icon.png")
		self.window.connect("destroy", self.destroy)
		self.window.connect("delete_event", self.delete_event)
		self.window.connect("window-state-event",self.icon)
		self.textview_chat = builder.get_object("textview_chat")
		self.chat_msg_entry = builder.get_object("chat_msg_entry")
		self.status = builder.get_object("status")
		self.client = BTClient(self.chat_msg_entry,self.textview_chat,self.status)
		self.server = BtServer(self.textview_chat,self.status,self.client)
		self.chat_msg_entry.connect("activate",self.client.reader)
		gtk.Tooltips().set_tip(self.chat_msg_entry,"type here for chatting", tip_private=None)		
		self.clear_button = builder.get_object("clear_button")
		self.clear_button.connect("clicked",self.clear_chat)
		gtk.Tooltips().set_tip(self.clear_button,"click here to clear the chatbox", tip_private=None)	
		self.change_nick_button = builder.get_object("change_nick_button")
		gtk.Tooltips().set_tip(self.change_nick_button,"click here to change your nickname", tip_private=None)	
		rand_nickname = "User-"+str(random.randint(10000,100000))
		self.client.set_nick(rand_nickname)
		self.change_nick_button.set_label(rand_nickname)
		self.change_nick_button.connect("clicked",self.change_nick)
		self.disconnect_button = builder.get_object("disconnect_button")
		self.disconnect_button.connect("clicked",self.disconnect)
		self.list_devices = gtk.ListStore(str, str)
		self.update_devices_button = builder.get_object("update_devices_button")
		self.devices_treeview = builder.get_object("devices_treeview")
		gtk.Tooltips().set_tip(self.devices_treeview,"available devices", tip_private=None)		
		self.update_devices_button.connect("clicked",self.lookup)
		cell = gtk.CellRendererText()  
		self.queue = Queue.Queue()
		self.queue2 = Queue.Queue()
        	coloumn0 = gtk.TreeViewColumn("Name", cell, text=0)  
         	coloumn1 = gtk.TreeViewColumn("Address", cell, text=1)  
	        self.devices_treeview.append_column(coloumn0)  
         	self.devices_treeview.append_column(coloumn1)  
           	store = gtk.TreeStore(gobject.TYPE_STRING)  
         	self.devices_treeview.set_model(store)  
        	self.devices_treeview.set_model(self.list_devices)  
		self.list_devices.append(["",""])	
		self.devices_treeview.connect("row-activated",self.row_connect,None)
		self.quit_menu_item = builder.get_object("quit_menu_item")
		self.quit_menu_item.connect("activate",self.destroy)
		self.about_dialog = builder.get_object("about_dialog")
		self.about_menu_item = builder.get_object("about_menu_item")
		self.about_menu_item.connect("activate",self.about)
		pynotify.init('pybtchat')
	    	self.window.show()

	def show(self):
		self.server.start()
		gtk.main()


Gui().show()

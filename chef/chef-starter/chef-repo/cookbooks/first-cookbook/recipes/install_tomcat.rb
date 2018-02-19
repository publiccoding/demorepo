#
# Cookbook:: .
# Recipe:: install_tomcat
#
# Copyright:: 2018, The Authors, All Rights Reserved.

pack_name = node['first-cookbook']['tomcat']

apt_update 'update' do
    action :update
end

package node['first-cookbook']['tomcat'] do
    action :install
    
end

service node['first-cookbook']['tomcat'] do
  action :start
end

package "tomcat-additional" do 
    package_name node['first-cookbook']['tomcat_addition'] 
    action :install
    
end 

# cookbook_file '/home/ubuntu/test.txt' do
#   source 'tomcat7'
#   action :create
# end

# template '/home/ubuntu/message.txt' do
#     source 'message.txt.erb'
#     action :create
# end

# template '/etc/tomcat7/tomcat-users.xml' do
#     source 'tomcat-users.xml.erb'
#     action :create
#     notifies :restart, "service[#{pack_name}]"
# end

# remote_file '/var/lib/tomcat7/webapps/sample.war' do
#   source 'https://tomcat.apache.org/tomcat-7.0-doc/appdev/sample/sample.war'
#   action :create
#   notifies :restart, "service[#{pack_name}]"
# end

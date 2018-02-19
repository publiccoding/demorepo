#
# Cookbook:: .
# Recipe:: install_tomcat
#
# Copyright:: 2018, The Authors, All Rights Reserved.

package 'tomcat7' do
  action :install
  only_if { node['platform']=='ubuntu' }
end

service 'tomcat7' do
  action :start
end

package 'tomcat' do
    action :install
    only_if { node['platform']=='redhat' }
    
end
  
service 'tomcat7' do
  action :nothing
end

#
# Cookbook:: first-cookbook
# Recipe:: default
#
# Copyright:: 2018, The Authors, All Rights Reserved.

package node['first-cookbook']['package_name'] do 
    action :install
end

service node['first-cookbook']['package_name'] do 
    action :restart 
end
file '/var/www/html/index.html' do 
    content 'Welcome to Apache ( controller server Demo)\n'
    action :create
end 
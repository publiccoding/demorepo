#
# Cookbook:: first-cookbook
# Recipe:: default
#
# Copyright:: 2018, The Authors, All Rights Reserved.

# Install multiple packages using array attribute 

package_names = node['first-cookbook']['package_name']

package_names.each do | package_name|
    package package_name do 
        action :remove
    end
end 

# If package_name can store array type then you below command 

# package 'multipleinstance' do 
#     package_name package_names
#     action :install
# end

#start the services 

# service node['first-cookbook']['package_name'] do 
#     action :restart 
# end

# change default file content 

# file '/var/www/html/index.html' do 
#     content 'Welcome to Apache ( controller server Demo)\n'
#     action :create
# end 


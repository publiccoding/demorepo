#
# Cookbook:: .
# Recipe:: install_ubuntu
#
# Copyright:: 2018, The Authors, All Rights Reserved.
package node['multirecipe']['package_name'] do
  action :install
  
end
# service node['multirecipe']['package_name'] do
#   action :restart
  
# end
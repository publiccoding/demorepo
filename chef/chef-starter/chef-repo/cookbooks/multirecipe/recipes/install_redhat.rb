#
# Cookbook:: .
# Recipe:: install_redhat
#
# Copyright:: 2018, The Authors, All Rights Reserved.


package node['multirecipe']['package_name'] do
  action :install
  
end
# service node['multirecipe']['package_name'] do
#   action :restart
  
# end
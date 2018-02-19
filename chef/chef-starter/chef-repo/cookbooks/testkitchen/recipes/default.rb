#
# Cookbook:: testkitchen
# Recipe:: default
#
# Copyright:: 2018, The Authors, All Rights Reserved.
apt_update 'update package' do
  action :update
  only_if { node['platform'] == "ubuntu" }
end

include_recipe 'testkitchen::utils'
include_recipe 'testkitchen::install_tomcat'
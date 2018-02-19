#
# Cookbook:: multirecipe
# Recipe:: default
#
# Copyright:: 2018, The Authors, All Rights Reserved.
if node['multirecipe']['tobeexecuted'] then 
    if node['platform'] == 'ubuntu'
        include_recipe 'multirecipe::install_ubuntu'
    elsif node['platform'] == 'redhat'
        include_recipe 'multirecipe::install_ubuntu'
    else
        #raise Error message       
    end

    include_recipe "multirecipe::configure"
end

service node['multirecipe']['package_name'] do
    action :restart
    only_if { node['platform'] == 'ubuntu' }
  end
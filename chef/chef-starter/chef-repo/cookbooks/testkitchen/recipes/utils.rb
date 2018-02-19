#
# Cookbook:: .
# Recipe:: utils
#
# Copyright:: 2018, The Authors, All Rights Reserved.

package 'utilities' do
    package_name node['testkitchen']['utility']
    action :install
end

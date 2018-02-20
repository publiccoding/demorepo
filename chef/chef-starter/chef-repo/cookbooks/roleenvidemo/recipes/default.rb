#
# Cookbook:: roleenvidemo
# Recipe:: default
#
# Copyright:: 2018, The Authors, All Rights Reserved.
include_recipe 'roleenvidemo::tomcat'
include_recipe 'nginx::default'
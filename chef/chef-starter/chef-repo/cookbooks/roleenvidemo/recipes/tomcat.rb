#
# Cookbook:: .
# Recipe:: tomcat
#
# Copyright:: 2018, The Authors, All Rights Reserved.

tomcat_install 'mytomcat' do
    version '7.0.84'
  end

  tomcat_service 'mytomcat' do
    action :start
        
  end
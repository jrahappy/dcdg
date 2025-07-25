from django.shortcuts import render
from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    template_name = 'landing/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['services'] = [
            {
                'icon': 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01',
                'title': 'Practice Management',
                'description': 'Streamline operations with our comprehensive practice management solutions.'
            },
            {
                'icon': 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
                'title': 'Financial Services',
                'description': 'Expert financial guidance and revenue cycle management for dental practices.'
            },
            {
                'icon': 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z',
                'title': 'HR & Staffing',
                'description': 'Complete HR solutions and staffing support for your dental team.'
            },
            {
                'icon': 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
                'title': 'Technology Solutions',
                'description': 'Cutting-edge dental technology and IT support services.'
            },
            {
                'icon': 'M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z M20.488 9H15V3.512A7.025 7.025 0 0120.488 9z',
                'title': 'Marketing & Growth',
                'description': 'Strategic marketing to grow your patient base and practice revenue.'
            },
            {
                'icon': 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
                'title': 'Training & Development',
                'description': 'Continuous education and professional development for your team.'
            }
        ]
        
        context['features'] = [
            {
                'title': 'Increased Efficiency',
                'description': 'Streamline operations and reduce administrative burden by up to 40%'
            },
            {
                'title': 'Cost Savings',
                'description': 'Leverage group purchasing power and shared services for significant savings'
            },
            {
                'title': 'Professional Growth',
                'description': 'Access to continuing education and career advancement opportunities'
            },
            {
                'title': 'Better Patient Care',
                'description': 'Focus on dentistry while we handle the business side'
            }
        ]
        
        return context

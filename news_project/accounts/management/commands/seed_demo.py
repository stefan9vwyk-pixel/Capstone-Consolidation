from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed demo users, publishers, articles, and newsletters'

    def handle(self, *args, **options):
        from accounts.models import CustomUser
        from news.models import Publisher, Article, Newsletter

        # Create demo users
        users_data = [
            {
                'username': 'admin', 
                'email': 'admin@newsroom.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'editor',
                'password': 'admin123',
                'is_staff': True,
                'is_superuser': True
            },
            {
                'username': 'editor1',
                'email': 'editor@newsroom.com',
                'first_name': 'Sarah',
                'last_name': 'Mitchell',
                'role': 'editor',
                'password': 'editor123'
            },
            {
                'username': 'journalist1',
                'email': 'journalist@newsroom.com',
                'first_name': 'James',
                'last_name': 'Carter',
                'role': 'journalist',
                'password': 'journalist123'
            },
            {
                'username': 'journalist2',
                'email': 'journalist2@newsroom.com',
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'role': 'journalist',
                'password': 'journalist123'
            },
            {
                'username': 'reader1',
                'email': 'reader@newsroom.com',
                'first_name': 'Alex',
                'last_name': 'Turner',
                'role': 'reader',
                'password': 'reader123'
            },
        ]

        created_users = {}
        for data in users_data:
            if not CustomUser.objects.filter(
                username=data['username']
            ).exists():
                user = CustomUser.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    role=data['role'],
                    password=data['password'],
                    is_staff=data.get('is_staff', False),
                    is_superuser=data.get('is_superuser', False),
                )
                created_users[data['username']] = user
                self.stdout.write(
                    f'  Created user: {user.username} ({user.role})'
                )
            else:
                created_users[data['username']] = CustomUser.objects.get(
                    username=data['username']
                )

        journalist1 = created_users.get('journalist1')
        journalist2 = created_users.get('journalist2')
        editor1 = created_users.get('editor1')

        # Create publishers
        if not Publisher.objects.exists():
            pub1 = Publisher.objects.create(
                name='The Daily Chronicle',
                description=(
                    'A leading national newspaper covering politics, '
                    'business, and culture.'
                ),
                website='https://dailychronicle.example.com',
            )
            pub1.editors.add(editor1)
            pub1.journalists.add(journalist1, journalist2)

            pub2 = Publisher.objects.create(
                name='Tech Insider Weekly',
                description=(
                    'Your source for the latest in technology, '
                    'startups, and innovation.'
                ),
                website='https://techinsider.example.com',
            )
            pub2.editors.add(editor1)
            pub2.journalists.add(journalist2)

            self.stdout.write('  Created publishers.')

        # Create articles
        if not Article.objects.exists():
            articles_data = [
                {
                    'title': (
                        'Global Climate Summit Reaches Historic Agreement'
                    ),
                    'content': (
                        'World leaders gathered in Geneva this week to sign '
                        'what many are calling the most significant climate '
                        'agreement in decades. The accord commits 195 '
                        'nations to reducing carbon emissions by 45% before '
                        '2035, with binding enforcement mechanisms that '
                        'previous agreements lacked.\n\nThe deal, brokered '
                        'after 72 hours of continuous negotiations, '
                        'includes a $500 billion green transition fund for '
                        'developing nations. Environmental groups have '
                        'cautiously welcomed the agreement while noting that '
                        'implementation details remain vague.\n\n"This is a '
                        'turning point," said UN Secretary-General Maria '
                        'Santos. "For the first time, we have teeth in our '
                        'commitments." Critics, however, point out that '
                        'several major industrial nations negotiated '
                        'exemptions for key sectors.\n\nMarkets reacted '
                        'positively to the news, with renewable energy stocks '
                        'surging across global exchanges. The agreement is '
                        'set to take effect in January 2026, pending '
                        'ratification by member states.'
                    ),
                    'author': journalist1,
                    'approved': True,
                    'publisher': Publisher.objects.first(),
                },
                {
                    'title': 'AI Startup Raises $2B in Record Funding Round',
                    'content': (
                        'San Francisco-based artificial intelligence '
                        'company NeuralPath has closed a $2 billion Series C '
                        'funding round, setting a new record for early-stage '
                        'AI investment. The round was led by Sequoia Capital '
                        'with participation from SoftBank, Google Ventures, '
                        'and several sovereign wealth funds.\n\n'
                        'NeuralPath, founded in 2023, develops large language '
                        'models specialized for enterprise use cases '
                        'including legal document analysis, medical diagnosis '
                        'support, and financial modeling. The company claims '
                        'its models achieve 40% better accuracy than '
                        'general-purpose alternatives on domain-specific '
                        'tasks.\n\n'
                        'CEO Dr. Aisha Patel said the funding will be used to '
                        'expand their research team from 200 to 800 employees '
                        'and establish data centers in Europe and Asia. The '
                        'company is reportedly valued at $18 billion '
                        'post-money.\n\nThe raise comes amid intense '
                        'competition in the enterprise AI space, with '
                        'Microsoft, Google, and Amazon all aggressively '
                        'expanding their own offerings.'
                    ),
                    'author': journalist2,
                    'approved': True,
                    'publisher': Publisher.objects.last(),
                },
                {
                    'title': 'Central Banks Signal Coordinated Rate Cuts',
                    'content': (
                        'The Federal Reserve, European Central Bank, and '
                        'Bank of England issued a rare joint statement '
                        'Tuesday signaling coordinated interest rate '
                        'reductions beginning next quarter. The '
                        'announcement sent bond yields tumbling and equity '
                        'markets to multi-month highs.\n\n'
                        'The three institutions cited easing inflation '
                        'pressures and growing concerns about economic '
                        'slowdown as the primary drivers. The Fed is '
                        'expected to cut rates by 50 basis points, while '
                        'the ECB and BoE are forecasting 25 basis point '
                        'reductions.\n\n'
                        'Economists were split on the wisdom of coordination. '
                        '"Synchronized easing amplifies the stimulus effect," '
                        'said Dr. Robert Chen of the Peterson Institute. '
                        '"But it also reduces the ability of individual '
                        'central banks to respond to country-specific '
                        'conditions."\n\n'
                        'Mortgage rates are expected to begin declining '
                        'within weeks of the announcement, providing relief '
                        'to housing markets that have been frozen by high '
                        'borrowing costs.'
                    ),
                    'author': journalist1,
                    'approved': False,
                    'publisher': Publisher.objects.first(),
                },
                {
                    'title': (
                        'New Study Links Urban Green Spaces to Mental Health'
                    ),
                    'content': (
                        'A comprehensive 10-year study involving 50,000 '
                        'participants across 12 cities has found that access '
                        'to urban parks and green spaces reduces rates of '
                        'anxiety and depression by up to 30%. The research, '
                        'published in The Lancet, is the largest '
                        'longitudinal study of its kind.\n\n'
                        'Researchers at Oxford University tracked '
                        'participants` mental health outcomes alongside '
                        'detailed geospatial data on their proximity to '
                        'parks, street trees, and community gardens. '
                        'The effect was found to be independent of income, '
                        'age, and pre-existing conditions.\n\n'
                        '"The evidence is now unambiguous," said lead '
                        'researcher Dr. Emma Blackwood. "Green space is '
                        'not a luxury amenity — it is a public health '
                        'necessity." The study recommends that city '
                        'planners allocate at least 15% of urban land '
                        'to accessible green space.\n\nSeveral major '
                        'cities have already cited the research in updated '
                        'zoning policies, with London, Paris, and Singapore '
                        'announcing expanded urban greening programs.'
                    ),
                    'author': journalist2,
                    'approved': True,
                    'publisher': None,
                },
                {
                    'title': (
                        'Breakthrough in Quantum Computing Achieves '
                        '1000-Qubit Milestone'
                        ),
                    'content': (
                        'IBM Research has announced a quantum processor '
                        'capable of sustaining 1,000 stable qubits, a '
                        'milestone that researchers say brings practical '
                        'quantum computing significantly closer. '
                        'Previous systems struggled to maintain coherence '
                        'beyond 400 qubits under real-world conditions.\n\n'
                        'The achievement relies on a novel error-correction '
                        'architecture that reduces decoherence — the primary '
                        'obstacle to scaling quantum systems. IBM\'s team '
                        'demonstrated the processor solving an optimization '
                        'problem in 3 minutes that would take classical '
                        'supercomputers an estimated 10,000 years.\n\n'
                        'The announcement has major implications for '
                        'cryptography, drug discovery, and logistics. '
                        'Current encryption standards, including '
                        'RSA-2048, could be vulnerable to quantum '
                        'attacks within the decade, prompting renewed '
                        'urgency around post-quantum cryptography '
                        'standards.\n\n'
                        'IBM plans to make the system available through '
                        'its cloud platform by mid-2026, with pricing '
                        'aimed at enterprise customers.'
                    ),
                    'author': journalist2,
                    'approved': True,
                    'publisher': Publisher.objects.last(),
                },
            ]

            created_articles = []
            for data in articles_data:
                article = Article.objects.create(**data)
                created_articles.append(article)
                self.stdout.write(
                    f'  Created article: {article.title[:50]}...'
                )

            # Create newsletters
            if created_articles and not Newsletter.objects.exists():
                nl1 = Newsletter.objects.create(
                    title='Weekly World Digest',
                    description=(
                        'A curated roundup of the most important global '
                        'stories from the past week, covering politics, '
                        'economics, and society.'
                    ),
                    author=journalist1,
                )
                nl1.articles.add(created_articles[0], created_articles[2])

                nl2 = Newsletter.objects.create(
                    title='Tech & Innovation Briefing',
                    description=(
                        'Stay ahead of the curve with our weekly '
                        'technology newsletter covering AI, startups, '
                        'and digital transformation.'
                    ),
                    author=journalist2,
                )
                nl2.articles.add(created_articles[1], created_articles[4])

                self.stdout.write('  Created newsletters.')

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Demo Login Credentials ==='))
        self.stdout.write('  Editor:     editor1 / editor123')
        self.stdout.write('  Journalist: journalist1 / journalist123')
        self.stdout.write('  Journalist: journalist2 / journalist123')
        self.stdout.write('  Reader:     reader1 / reader123')
        self.stdout.write('  Admin:      admin / admin123')

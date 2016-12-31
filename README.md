# TimerWheel
分层时间轮法

游戏中用到timer来实现各种各样的功能。包括状态的添加，法术场、气劲、激光等的表现、结算等效果。这样的timer会频繁的添加与删除。最近发现netty
使用的是hashedtimerwheel，顺便就研究了下这方面的功能。
发现 这篇文章进行了详细的介绍：  http://novoland.github.io/%E5%B9%B6%E5%8F%91/2014/07/26/%E5%AE%9A%E6%97%B6%E5%99%A8%EF%BC%88Timer%EF%BC%89%E7%9A%84%E5%AE%9E%E7%8E%B0.html
英文原版的可以在Hashed and Hierarchical Timing Wheels: Efﬁcient Data Structures for Implementing a Timer Facility这篇论文上看到。
但是苦恼的是，网上实现包括netty都是实现了论文中的第二种优化，没有实现Hierarchical timing wheel,所以就动手实现了一下。
timerwheel实现了一个类似 netty的不分层的时间轮。
HierarchicalTimerWheel类实现了一个分成的时间轮。默认设置最小轮是游戏的帧，最大轮支持小时，并且支持rounds，理论上所有的timer都可以由其来实现。
具体的信息见代码。
增加缓存事件的功能，同时封闭玩家对timer的直接引用。
